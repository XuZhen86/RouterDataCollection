install:
	pip3 install --use-pep517 .

install-dev:
	pip3 install --use-pep517 --editable .

uninstall:
	pip3 uninstall --yes router-data-collection

clean:
	rm -rf *.egg-info build

docker-image:
	docker build --pull --no-cache --tag router-data-collection .
