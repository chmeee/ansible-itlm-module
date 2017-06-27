#!/usr/bin/python

from ansible.module_utils.basic import *
import csv
import requests
import json

__author__ = "Ildefonso Montero Perez"
__version__ = "0.0.1"

request = "http://localhost:8080/api/v1/policy-automation/scenarios/"
token = <INTELLIMENT-API-TOKEN>
headers = {"Accept" : "application/json", "content-type" : "application/json", "Authorization" : "Bearer " + token}

def create_requirements(policies, scenario_id):
	""" Creates visibility requirements on Intelliment Model based on policies defined by Ansible playbook """
	internet = get_internet_id(scenario_id)

	for policy in policies:

		source = ""
		source_type = ""
		destination = ""
		destination_type = ""

		tag_src = policy["source"]
		tag_dst = policy["destination"]

		server = request + scenario_id + "/objects?name=i-*"
		response = requests.get(server, headers = headers)
		data = response.json()["data"]

		for obj in data:
			if "tags" in obj.keys():
				for t in obj["tags"]:
					if t == tag_src:
						source = obj["id"]
						source_type = "id"
					if t == tag_dst:
						destination = obj["id"]
						destination_type = "id"

		if source == "":
			source = policy["source"]
			server = request + scenario_id + "/objects?name=" + source
			response = requests.get(server, headers = headers)
			data = response.json()["data"]
			for obj in data:
				source = obj["id"]
				source_type = "id"

			if source_type == "":
				source_type = "ip"
				if source == "0.0.0.0/0":
					source = internet
					source_type = "id"

		if destination == "":
			destination = policy["destination"]
			server = request + scenario_id + "/objects?name=" + destination
			response = requests.get(server, headers = headers)
			data = response.json()["data"]
			for obj in data:
				destination = obj["id"]
				destination_type = "id"

			if destination_type == "":
				destination_type = "ip"
				if destination == "0.0.0.0/0":
					destination = internet
					destination_type = "id"

		action = policy["action"]
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

		if is_aws_related(source) or is_aws_related(destination):
			aws_related_element = get_aws_related(source, destination)
			aws_related_element_type = get_aws_related_type(source, destination)

			if needs_sg(aws_related_element):
				namefield = "sg*"
				tag = "aws-sg"
			else:
				namefield = "acl*"
				tag = "aws-acl"

			server = request + scenario_id + "/objects?types=objects_group&name=" + namefield
			response = requests.get(server, headers = headers)
			data = response.json()["data"]

			for obj in data:
				obj_id = obj["id"]
				if "objects" in obj.keys():
					for net in obj["objects"]:
						if net["id"] == aws_related_element:
							if aws_related_element_type == "source":
								payload = {
									"action": action,
									"source": {
										"type": "id",
										"value": obj_id
									},
									"destination": {
										"type": destination_type,
										"value": destination
									},
									"configuration": [{
										"enabled": True,
										"type": "custom",
										"services": services
									}],
									"tags" : [tag]
								}
							else:
								payload = {
									"action": action,
									"source": {
										"type": source_type,
										"value": source
									},
									"destination": {
										"type": "id",
										"value": obj_id
									},
									"configuration": [{
										"enabled": True,
										"type": "custom",
										"services": services
									}],
									"tags" : [tag]
								}
							server = request + scenario_id + "/requirements"
							requests.post(server, headers = headers, data = json.dumps(payload))
							time.sleep(1)
		else:
			tag = source + "-" + destination

			payload = {
				"action": action,
				"source": {
					"type": source_type,
					"value": source
				},
				"destination": {
					"type": destination_type,
					"value": destination
				},
				"configuration": [{
					"enabled": True,
					"type": "custom",
					"services": services
				}],
				"tags" : [tag]
			}

			server = request + scenario_id + "/requirements"
			requests.post(server, headers = headers, data = json.dumps(payload))
			time.sleep(1)

def get_internet_id(scenario_id):
    """ Return the id of internet element on scenario attached to AWS """
    server = request + scenario_id +  "/objects?types=internet"
    response = requests.get(server, headers = headers)
    data = response.json()["data"]
    return data[0]["id"]

def get_aws_related(source, destination):
	if is_aws_related(source):
		return source
	else:
		return destination

def get_aws_related_type(source, destination):
	if is_aws_related(source):
		return "source"
	else:
		return "destination"

def is_aws_related(source):
	return needs_acl(source) or needs_sg(source)

def needs_acl(source):
	return str(source).startswith("subnet-")

def needs_sg(source):
	return str(source).startswith("i-")

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
