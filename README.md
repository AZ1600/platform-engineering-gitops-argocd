# Platform Engineering GitOps with ArgoCD

## Overview

This project demonstrates GitOps-based continuous delivery using ArgoCD and Kubernetes.

Application deployments are managed through declarative Kubernetes manifests stored in GitHub. ArgoCD continuously monitors the repository and synchronizes the desired state to the Kubernetes cluster.

## Architecture

GitHub

↓

ArgoCD

↓

Amazon EKS

↓

Kubernetes Application Deployment

## Technologies

* AWS
* Amazon EKS
* Kubernetes
* ArgoCD
* GitHub
* GitOps

## Components

### Deployment

A Kubernetes Deployment manages application replicas and container lifecycle.

### Service

A Kubernetes Service provides internal network access to the application.

## Benefits of GitOps

* Declarative infrastructure management
* Automated synchronization
* Version-controlled deployments
* Rollback capability
* Improved operational consistency

## Project Structure

platform-engineering-gitops-argocd/

├── README.md

└── manifests/

├── deployment.yaml

└── service.yaml

## Learning Outcomes

* GitOps principles
* Kubernetes deployments
* Kubernetes services
* Continuous delivery
* Platform engineering practices
* ArgoCD architecture
## Screenshots

### ArgoCD Application

![ArgoCD Application](docs/screenshots/argocd-healthy-synced.png)

### Kubernetes Resources

![Kubernetes Resources](docs/screenshots/kubectl-resources.png)
