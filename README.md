# ansible-itlm-module

Proof of Concept of Ansible integration with Intelliment Security Policy Automation. This integration shows how to define network visibility requirements as code using Ansible as provisioning tool.

### Who can use this integration?

*DevOps* and *NetOps* that:

+ Do an advanced configuration management with Ansible
+ Want to automate all aspects of IT management

*Benefits*:

+ Define network visibility requirements with each component of your applications
+ Provision - decomission automatically with each application or component change
+ No need for manual operation to get network visibility
+ Graphical visualization of network visibility changes

## How to run

+ Edit intelliment.yml to define your network visibility needs, specifying source, destination, action and services. Source and destination could be defined as IP, name or tag inside Intelliment model.

```yaml
---
- hosts: localhost
  gather_facts: false
  connection: local

  tasks:
    - name: Create visibility requirements on Intelliment
      intelliment: 
        scenario: 15
        policies:
          - source: "0.0.0.0/0"
            destination: "eu-banking-app"
            action: "allow"
            services: "tcp/80"
          - source: "i-034ee5dbfd85f6837"
            destination: "0.0.0.0/0"
            action: "allow"
            services: "tcp/75"
          - source: "0.0.0.0/0"
            destination: "subnet-79972720"
            action: "allow"
            services: "tcp/60-100"
          - source: "subnet-79972720"
            destination: "0.0.0.0/0"
            action: "allow"
            services: "tcp/200-300"          
          - source: "B_intranet"
            destination: "backend-1"
            action: "allow"
            services: "tcp/443"
      register: result
```

+ Launch playbook: `ansible-playbook intelliment.yml`

## Demo

Following you can see a short video with a demo showing how to define network visibilities using Ansible and Intelliment and deploying them in a heterogeneous network infrastructure.

[![Intelliment and Ansible integration](https://img.youtube.com/vi/Ennv8eF_QRw/0.jpg)](https://youtu.be/Ennv8eF_QRw)

If you want more info, please contact us at sales@intellimentsec.com