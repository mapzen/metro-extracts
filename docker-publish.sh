#!/bin/sh

repo="$1"
tag="$2"

tag=$(echo $tag | sed 's/[^-._0-9a-zA-Z]/-/g') # convert invalid chars to '-'

docker build --rm=false -t $repo .

aws ecr get-login --region us-east-1 | bash
docker tag $repo $ECR_HOST/$repo:$tag
docker push $ECR_HOST/$repo:$tag
