#!/usr/bin/python

DOCUMENTATION = '''
---
module: ansible-itlm-module (intelliment)
short_description: Create visibility requirements on Intelliment. Source and destination could be defined as IP, name or tags.
'''

EXAMPLES = '''
- name: Example of creation by IP, name and/or tags
      intelliment:
        scenario: 1
        policies:
          - source: "0.0.0.0/0"
            destination: "eu-banking-app"
            action: "allow"
            services: "tcp/33"
          - source: "10.0.2.0/24"
            destination: "10.21.30.0/24"
            action: "allow"
            services: "tcp/90"
          - source: "0.0.0.0/0"
            destination: "subnet-79972720"
            action: "allow"
            services: "tcp/60-100"
          - source: "B_intranet"
            destination: "backend-1"
            action: "allow"
            services: "tcp/80"
      register: result
'''

from ansible.module_utils.basic import *
import csv
import requests
import json

__author__ = "Ildefonso Montero Perez"
__version__ = "0.0.1"

request = "http://localhost:8080/api/v1/policy-automation/scenarios/"
token = <INTELLIMENT-API-TOKEN>
headers = {"Accept" : "application/json", "content-type" : "application/json", "Authorization" : "Bearer " + token}

""" 
 Creates visibility requirements on Intelliment model based on policies defined by Ansible playbook.
 For each policy defined on playbook, it resolves its fields and creates a requirement solving sources/destination for AWS related 
"""
def create_requirements(policies, scenario_id):
		
	internet = get_internet_id(scenario_id)

	for policy in policies:

		requirement = {
			"action": resolve_action(policy),
			"source": "",
			"destination": "",
			"configuration": [{
				"enabled": True,
				"type": "custom",
				"services": resolve_services(policy)
			}],
			"tags" : ""
		}

		policy_endpoints = resolve_endpoints(scenario_id, policy, internet)

		if is_aws_related(policy_endpoints):
			create_aws_related_requirement(scenario_id, requirement, policy_endpoints)
		else:
			tag = policy_endpoints["source"] + "-" + policy_endpoints["destination"]
			create_requirement(scenario_id, requirement, tag, policy_endpoints["source"], policy_endpoints["source_type"], policy_endpoints["destination"], policy_endpoints["destination_type"])

""" 
 Creates AWS related requirement solving its security group or network ACL related 
"""
def create_aws_related_requirement(scenario_id, requirement, policy_endpoints):
	
	aws = get_aws_fields(policy_endpoints)
	server = request + scenario_id + "/objects?types=objects_group&name=" + aws["aws_namefield"]
	response = requests.get(server, headers = headers)
	data = response.json()["data"]
		
	for obj in data:
		obj_id = obj["id"]
		if "objects" in obj.keys():
			for net in obj["objects"]:
				if net["id"] == aws["aws_related_element"]:
					if aws["aws_related_element_type"] == "source":
						create_requirement(scenario_id, requirement, aws["aws_tag"], obj_id, "id", policy_endpoints["destination"], policy_endpoints["destination_type"])
					else:
						create_requirement(scenario_id, requirement, aws["aws_tag"], policy_endpoints["source"], policy_endpoints["source_type"], obj_id, "id")

""" 
 Creates a requirement via Intelliment API 
"""
def create_requirement(scenario_id, requirement, tag, source, source_type, destination, destination_type):
	
	requirement["tags"] = [tag]
	requirement["source"] = {
		"type": source_type,
		"value": source
	}
	requirement["destination"] = {
		"type": destination_type,
		"value": destination
	}			
	server = request + scenario_id + "/requirements"
	requests.post(server, headers = headers, data = json.dumps(requirement))
	time.sleep(1)

""" 
 Return the id of internet element on scenario attached to AWS 
"""
def get_internet_id(scenario_id):
    
    server = request + scenario_id +  "/objects?types=internet"
    response = requests.get(server, headers = headers)
    data = response.json()["data"]
    return data[0]["id"]

""" 
 Resolves policies endpoints (source and destination) identified by tags, IPs and/or names 
"""
def resolve_endpoints(scenario_id, policy, internet):
	
	policy_endpoints = {
		"source" : "",
		"source_type" : "",
		"destination" : "",
		"destination_type" : ""
	}

	policy_endpoints = resolve_endpoints_by_tags(scenario_id, policy, policy_endpoints)
	policy_endpoints = resolve_enpoint(scenario_id, "source", "source_type", internet, policy, policy_endpoints)
	policy_endpoints = resolve_enpoint(scenario_id, "destination", "destination_type", internet, policy, policy_endpoints)

	return policy_endpoints

""" 
 Resolves endpoint by field and field type 
"""
def resolve_enpoint(scenario_id, field, field_type, internet, policy, policy_endpoints):
	
	if policy_endpoints[field] == "":
		policy_endpoints[field] = policy[field]
		server = request + scenario_id + "/objects?name=" + policy_endpoints[field]
		response = requests.get(server, headers = headers)
		data = response.json()["data"]
		for obj in data:
			policy_endpoints[field] = obj["id"]
			policy_endpoints[field_type] = "id"

		if policy_endpoints[field_type] == "":
			policy_endpoints[field_type] = "ip"
			if policy_endpoints[field] == "0.0.0.0/0":
				policy_endpoints[field] = internet
				policy_endpoints[field_type] = "id"

	return policy_endpoints

""" 
 Resolves policies endpoints (source and destination) by tags 
  TODO: need API endpoint for filtering objects by tags
"""
def resolve_endpoints_by_tags(scenario_id, policy, policy_endpoints):
	
	tag_src = policy["source"]
	tag_dst = policy["destination"]

	""" FIXME: coupled to perform a filter by name due to limitation of results via API """
	server = request + scenario_id + "/objects?name=i-*"
	response = requests.get(server, headers = headers)
	data = response.json()["data"]

	for obj in data:
		if "tags" in obj.keys():
			for t in obj["tags"]:
				if t == tag_src:
					policy_endpoints["source"] = obj["id"]
					policy_endpoints["source_type"] = "id"
				if t == tag_dst:
					policy_endpoints["destination"] = obj["id"]
					policy_endpoints["destination_type"] = "id"
	
	return policy_endpoints

""" 
 Resolves action from a policy 
"""
def resolve_action(policy):
	return policy["action"]

""" 
 Resolves services from a policy configuration 
"""
def resolve_services(policy):
	
	service = policy["services"].split("/")[0]
	if is_range(policy["services"].split("/")[1]):
		service_from = policy["services"].split("/")[1].split("-")[0]
		service_to = policy["services"].split("/")[1].split("-")[1]
	else:
		service_from = policy["services"].split("/")[1]
		service_to = policy["services"].split("/")[1]

	services = []
	services.append({
		"name": service + service_from + "_" + service_to,
		"type": service + "_service",
		"sourcePorts": "",
		"destinationPorts": service_from + ":" + service_to
	},)

	return services

""" 
 Checks if AWS related any of the endpoints 
"""
def is_aws_related(policy_endpoints):

	source = policy_endpoints["source"]
	destination = policy_endpoints["destination"]
	return is_aws_related_element(source) or is_aws_related_element(destination)

""" 
 Return AWS fields related with the endpoints 
"""
def get_aws_fields(policy_endpoints):
	
	source = policy_endpoints["source"]
	destination = policy_endpoints["destination"]
	aws_related_element = get_aws_related(source, destination)
	aws_namefield = get_aws_namefield(aws_related_element)

	aws = {
		"aws_related_element" : aws_related_element,
		"aws_related_element_type" : get_aws_related_type(source, destination),
		"aws_namefield" : aws_namefield,
		"aws_tag" : get_aws_tag(aws_namefield)
	}

	return aws

""" 
 Return AWS namefield by related element
"""
def get_aws_namefield(aws_related_element):
	
	if needs_sg(aws_related_element):
		return "sg*"
	else:
		return "acl*"

""" 
 Return AWS tag by namefield
"""
def get_aws_tag(aws_namefield):
	
	if "sg*" == aws_namefield:
		return "aws-sg"
	else:
		return "aws-acl"

""" 
 Return AWS related element by source or destination
"""
def get_aws_related(source, destination):
	if is_aws_related_element(source):
		return source
	else:
		return destination

""" 
 Return AWS related element type by source or destination
"""
def get_aws_related_type(source, destination):
	if is_aws_related_element(source):
		return "source"
	else:
		return "destination"

""" 
 Checks if element is AWS related
"""
def is_aws_related_element(element):
	return needs_acl(element) or needs_sg(element)

""" 
 Checks if element needs to be related with AWS network ACL
"""
def needs_acl(element):
	return str(element).startswith("subnet-")

""" 
 Checks if element needs to be related with AWS security group
"""
def needs_sg(element):
	return str(element).startswith("i-")

""" 
 Checks if a service is a range
"""
def is_range(service):
	return str(service).find("-") != -1

def main():

	fields = {"policies": {"required": True, "type": "list"},"scenario": {"required": True, "type": "str"}}

	module = AnsibleModule(argument_spec=fields)
	policies = module.params['policies']
	scenario = module.params['scenario']

	data = create_requirements(policies, scenario)
	module.exit_json(changed=False, meta=data)

if __name__ == '__main__':  
    main()
