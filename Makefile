registry_repository=ops

export GOPROXY=https://goproxy.cn

image:
	docker build --build-arg git_url=${GOPRIVATE_GIT_URL} --build-arg git_url_instand_of=${GOPRIVATE_GIT_URL_INSTEAD_OF} --tag=${REGISTRY_ENDPOINT}/${REGISTRY_NAMESPACE}/${registry_repository}:${IMAGE_TAG} .
