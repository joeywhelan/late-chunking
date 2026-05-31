# Late Chunking Retrieval Experiment
## Contents
1.  [Summary](#summary)
2.  [Presentation](#presentation)
3.  [Architecture](#architecture)
4.  [Features](#features)
5.  [Prerequisites](#prerequisites)
6.  [Installation](#installation)
7.  [Usage](#usage)

## Summary <a name="summary"></a>
This is a demonstration usage of late chunking via a Jina embedding model and Elastic vector database capabilities.

## Presentation <a name="presentation"></a>
https://joeywhelan.github.io/late-chunking/

## Architecture <a name="architecture"></a>
![architecture](assets/arch.png) 

## Features <a name="features"></a>
- Jupyter notebook
- Builds an Elastic Serverless deployment via Terraform
- Indexes two data sets and then compares late chunking performance on each
- Deletes the entire deployment via Terraform

## Prerequisites <a name="prerequisites"></a>
- uv
- terraform
- Elastic Cloud account and API key
- Jina API key
- Python

## Installation <a name="installation"></a>
- Edit the terraform.tfvars.sample and rename to terraform.tfvars
- Create a Python virtual environment

## Usage <a name="usage"></a>
- Execute notebook