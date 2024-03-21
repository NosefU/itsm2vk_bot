# Makefile

proj_name := $(shell basename "$(CURDIR)")

update:
	@git pull
	@docker build -t $(proj_name):latest .
	@docker rm -f $(proj_name)
	@docker run -d --env-file=.env --restart on-failure:10 --name $(proj_name) $(proj_name):latest

build:
	@docker build -t $(proj_name):latest .

hard_restart:
	@docker rm -f $(proj_name)
	@docker run -d --env-file=.env --restart on-failure:10 --name $(proj_name) $(proj_name):latest
