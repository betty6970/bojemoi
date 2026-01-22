#!/bin/bash

GITLAB_CONTAINER=$(docker ps -q -f name=gitlab_gitlab.1)
RUNNER_CONTAINER=$(docker ps -q -f name=gitlab_gitlab-runner)

case "$1" in
    status)
        echo "=== GitLab Status ==="
        docker exec -it $GITLAB_CONTAINER gitlab-ctl status
        ;;
    
    logs)
        service=${2:-""}
        if [ -z "$service" ]; then
            docker exec -it $GITLAB_CONTAINER gitlab-ctl tail
        else
            docker exec -it $GITLAB_CONTAINER gitlab-ctl tail $service
        fi
        ;;
    
    backup)
        echo "Creating backup..."
        docker exec -it $GITLAB_CONTAINER gitlab-backup create
        ;;
    
    check)
        echo "Running health checks..."
        docker exec -it $GITLAB_CONTAINER gitlab-rake gitlab:check
        ;;
    
    runner-list)
        echo "=== Registered Runners ==="
        docker exec -it $RUNNER_CONTAINER gitlab-runner list
        ;;
    
    runner-register)
        token=$2
        if [ -z "$token" ]; then
            echo "Usage: $0 runner-register TOKEN"
            exit 1
        fi
        docker exec -it $RUNNER_CONTAINER gitlab-runner register \
            --non-interactive \
            --url "https://gitlab.bojemoi.lab.local" \
            --registration-token "$token" \
            --executor "docker" \
            --docker-image "docker:24-dind" \
            --description "swarm-deployer" \
            --tag-list "swarm,deploy" \
            --docker-privileged \
            --docker-volumes "/var/run/docker.sock:/var/run/docker.sock"
        ;;
    
    *)
        echo "Usage: $0 {status|logs|backup|check|runner-list|runner-register}"
        exit 1
        ;;
esac

