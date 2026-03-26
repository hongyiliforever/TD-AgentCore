#!/bin/bash

set -e

REPO_URL=http://10.1.207.194:8081/ncdf/nc/nc-copilot/an-copilot-toolkits/wg-copilot/td-copilot-gpt.git

build_docker_func(){
  docker build --network=host --no-cache --progress=plain -t $IMAGE_NAME -f Dockerfile .
  echo "$IMAGE_NAME docker image created"
}

push_docker_func(){
  if [ -n "${HARBOR_ADDRESS}" ]; then
    docker login http://$HARBOR_ADDRESS -u "$HARBOR_USERNAME" -p "$HARBOR_PASSWORD"
    docker image tag $IMAGE_NAME $HARBOR_ADDRESS/$IMAGE_NAME
    docker push $HARBOR_ADDRESS/$IMAGE_NAME
    echo "$IMAGE_NAME docker image pushed to $HARBOR_ADDRESS"
    docker rmi $HARBOR_ADDRESS/$IMAGE_NAME
  fi
}

main(){
  if [ -z "$1" ]; then
    echo "没有提供分支或标签参数，将克隆默认分支。"
    BRANCH=""
  else
    echo "准备克隆分支或标签：$1"
    BRANCH="-b $1"
  fi
  WORK_DIR=$(dirname $(mktemp -u))
  REPO_NAME=$(basename ${REPO_URL%.git})
  if [ ! -d $WORK_DIR ]; then
    mkdir -p $WORK_DIR
  fi
  cd $WORK_DIR
  rm -rf $REPO_NAME

  git clone $BRANCH $REPO_URL
  cd $REPO_NAME

  cp pyproject.toml docker/
  cp -r src docker
  PROJECT_NAME=$(grep 'name = ' pyproject.toml | head -1 | awk -F'"' '{print $2}')
  PROJECT_VERSION=$(grep 'version = ' pyproject.toml | head -1 | awk -F'"' '{print $2}')
  PLATFORM=$(uname -m)
  IMAGE_NAME="nc/"$PROJECT_NAME"_"$PLATFORM:$PROJECT_VERSION
  cd docker
  echo "===================================================================="
  echo "当前工作目录: $(pwd)/$REPO_NAME"
  echo "项目名称: $PROJECT_NAME"
  echo "分支/TAG: $BRANCH"
  echo "项目版本: $PROJECT_VERSION"
  echo "平台: $PLATFORM"
  echo "镜像名称: $IMAGE_NAME"
  echo "===================================================================="

  while true
  do
    read -p "将制作 $IMAGE_NAME, 确认请输入(Y/N): " input

    case $input in
        [yY])
        build_docker_func
        push_docker_func
        exit 0
        ;;

        [nN])
        exit 1
        ;;

        *)
        echo "无效的输入"
        ;;
    esac
  done
}

main "$@"
