#!/usr/bin/env python3

import argparse
import fileinput
import logging
import os
import platform
import subprocess
import sys
import time
import urllib.request
from shutil import move, unpack_archive, which
from typing import Dict

logging.basicConfig(
	filename="easy-install.log",
	filemode="w",
	format="%(asctime)s - %(levelname)s - %(message)s",
	level=logging.INFO,
)


def cprint(*args, level: int = 1):
	"""
	logs colorful messages
	level = 1 : RED
	level = 2 : GREEN
	level = 3 : YELLOW

	default level = 1
	"""
	CRED = "\033[31m"
	CGRN = "\33[92m"
	CYLW = "\33[93m"
	reset = "\033[0m"
	message = " ".join(map(str, args))
	if level == 1:
		print(CRED, message, reset)
	if level == 2:
		print(CGRN, message, reset)
	if level == 3:
		print(CYLW, message, reset)


def clone_frappe_docker_repo() -> None:
	try:
		urllib.request.urlretrieve(
			"https://github.com/frappe/frappe_docker/archive/refs/heads/main.zip",
			"frappe_docker.zip",
		)
		logging.info("Downloaded frappe_docker zip file from GitHub")
		unpack_archive(
			"frappe_docker.zip", "."
		)  # Unzipping the frappe_docker.zip creates a folder "frappe_docker-main"
		move("frappe_docker-main", "frappe_docker")
		logging.info("Unzipped and Renamed frappe_docker")
		os.remove("frappe_docker.zip")
		logging.info("Removed the downloaded zip file")
	except Exception as e:
		logging.error("Download and unzip failed", exc_info=True)
		cprint("\nCloning frappe_docker Failed\n\n", "[ERROR]: ", e, level=1)


def get_from_env(dir, file) -> Dict:
	env_vars = {}
	with open(os.path.join(dir, file)) as f:
		for line in f:
			if line.startswith("#") or not line.strip():
				continue
			key, value = line.strip().split("=", 1)
			env_vars[key] = value
	return env_vars


def write_to_env(
	wd: str,
	sites,
	db_pass: str,
	admin_pass: str,
	email: str,
	erpnext_version: str = None,
) -> None:
	quoted_sites = ",".join([f"`{site}`" for site in sites]).strip(",")
	example_env = get_from_env(wd, "example.env")
	erpnext_version = erpnext_version or example_env["ERPNEXT_VERSION"]
	with open(os.path.join(wd, ".env"), "w") as f:
		f.writelines(
			[
				f"ERPNEXT_VERSION={erpnext_version}\n",  # defaults to latest version of ERPNext
				f"DB_PASSWORD={db_pass}\n",
				"DB_HOST=db\n",
				"DB_PORT=3306\n",
				"REDIS_CACHE=redis-cache:6379\n",
				"REDIS_QUEUE=redis-queue:6379\n",
				"REDIS_SOCKETIO=redis-socketio:6379\n",
				f"LETSENCRYPT_EMAIL={email}\n",
				f"SITE_ADMIN_PASS={admin_pass}\n",
				f"SITES={quoted_sites}\n",
			]
		)


def generate_pass(length: int = 12) -> str:
	"""Generate random hash using best available randomness source."""
	import math
	import secrets

	if not length:
		length = 56

	return secrets.token_hex(math.ceil(length / 2))[:length]


def check_repo_exists() -> bool:
	return os.path.exists(os.path.join(os.getcwd(), "frappe_docker"))


def setup_prod(project: str, sites, email: str, version: str = None, image = None) -> None:
	if len(sites) == 0:
		sites = ["site1.localhost"]

	if check_repo_exists():
		compose_file_name = os.path.join(os.path.expanduser("~"), f"{project}-compose.yml")
		docker_repo_path = os.path.join(os.getcwd(), "frappe_docker")
		cprint(
			"\nPlease refer to .example.env file in the frappe_docker folder to know which keys to set\n\n",
			level=3,
		)
		admin_pass = ""
		db_pass = ""
		with open(compose_file_name, "w") as f:
			# Writing to compose file
			if not os.path.exists(os.path.join(docker_repo_path, ".env")):
				admin_pass = generate_pass()
				db_pass = generate_pass(9)
				write_to_env(docker_repo_path, sites, db_pass, admin_pass, email, version)
				cprint(
					"\nA .env file is generated with basic configs. Please edit it to fit to your needs \n",
					level=3,
				)
				with open(os.path.join(os.path.expanduser("~"), "passwords.txt"), "w") as en:
					en.writelines(f"ADMINISTRATOR_PASSWORD={admin_pass}\n")
					en.writelines(f"MARIADB_ROOT_PASSWORD={db_pass}\n")
			else:
				env = get_from_env(docker_repo_path, ".env")
				admin_pass = env["SITE_ADMIN_PASS"]
				db_pass = env["DB_PASSWORD"]
			try:
				# TODO: Include flags for non-https and non-erpnext installation
				subprocess.run(
					[
						which("docker"),
						"compose",
						"--project-name",
						project,
						"-f",
						"compose.yaml",
						"-f",
						"overrides/compose.mariadb.yaml",
						"-f",
						"overrides/compose.redis.yaml",
						# "-f", "overrides/compose.noproxy.yaml", TODO: Add support for local proxying without HTTPs
						"-f",
						"overrides/compose.https.yaml",
						"--env-file",
						".env",
						"config",
					],
					cwd=docker_repo_path,
					stdout=f,
					check=True,
				)

			except Exception:
				logging.error("Docker Compose generation failed", exc_info=True)
				cprint("\nGenerating Compose File failed\n")
				sys.exit(1)

		# Use custom image
		if image:
			for line in fileinput.input(compose_file_name, inplace=True):
				if "image: frappe/erpnext" in line:
					line = line.replace("image: frappe/erpnext", f"image: {image}")
				sys.stdout.write(line)

		try:
			# Starting with generated compose file
			subprocess.run(
				[
					which("docker"),
					"compose",
					"-p",
					project,
					"-f",
					compose_file_name,
					"up",
					"-d",
				],
				check=True,
			)
			logging.info(f"Docker Compose file generated at ~/{project}-compose.yml")

		except Exception as e:
			logging.error("Prod docker-compose failed", exc_info=True)
			cprint(" Docker Compose failed, please check the container logs\n", e)
			sys.exit(1)

		for sitename in sites:
			create_site(sitename, project, db_pass, admin_pass)

	else:
		install_docker()
		clone_frappe_docker_repo()
		setup_prod(project, sites, email, version, image)  # Recursive


def setup_dev_instance(project: str):
	if check_repo_exists():
		try:
			subprocess.run(
				[
					"docker",
					"compose",
					"-f",
					"devcontainer-example/docker-compose.yml",
					"--project-name",
					project,
					"up",
					"-d",
				],
				cwd=os.path.join(os.getcwd(), "frappe_docker"),
				check=True,
			)
			cprint(
				"Please go through the Development Documentation: https://github.com/frappe/frappe_docker/tree/main/development to fully complete the setup.",
				level=2,
			)
			logging.info("Development Setup completed")
		except Exception as e:
			logging.error("Dev Environment setup failed", exc_info=True)
			cprint("Setting Up Development Environment Failed\n", e)
	else:
		install_docker()
		clone_frappe_docker_repo()
		setup_dev_instance(project)  # Recursion on goes brrrr


def install_docker():
	if which("docker") is not None:
		return
	cprint("Docker is not installed, Installing Docker...", level=3)
	logging.info("Docker not found, installing Docker")
	if platform.system() == "Darwin" or platform.system() == "Windows":
		print(
			f"""
            This script doesn't install Docker on {"Mac" if platform.system()=="Darwin" else "Windows"}.

            Please go through the Docker Installation docs for your system and run this script again"""
		)
		logging.debug("Docker setup failed due to platform is not Linux")
		sys.exit(1)
	try:
		ps = subprocess.run(
			["curl", "-fsSL", "https://get.docker.com"],
			capture_output=True,
			check=True,
		)
		subprocess.run(["/bin/bash"], input=ps.stdout, capture_output=True)
		subprocess.run(
			["sudo", "usermod", "-aG", "docker", str(os.getenv("USER"))], check=True
		)
		cprint("Waiting Docker to start", level=3)
		time.sleep(10)
		subprocess.run(["sudo", "systemctl", "restart", "docker.service"], check=True)
	except Exception as e:
		logging.error("Installing Docker failed", exc_info=True)
		cprint("Failed to Install Docker\n", e)
		cprint("\n Try Installing Docker Manually and re-run this script again\n")
		sys.exit(1)


def create_site(
	sitename: str,
	project: str,
	db_pass: str,
	admin_pass: str,
):
	cprint(f"\nCreating site: {sitename} \n", level=3)

	try:
		subprocess.run(
			[
				which("docker"),
				"compose",
				"-p",
				project,
				"exec",
				"backend",
				"bench",
				"new-site",
				sitename,
				"--no-mariadb-socket",
				"--db-root-password",
				db_pass,
				"--admin-password",
				admin_pass,
				"--install-app",
				"erpnext",
				"--set-default",
			],
			check=True,
		)
		logging.info("New site creation completed")
	except Exception as e:
		logging.error(f"Bench site creation failed for {sitename}", exc_info=True)
		cprint(f"Bench Site creation failed for {sitename}\n", e)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Install Frappe with Docker")
	parser.add_argument(
		"-p", "--prod", help="Setup Production System", action="store_true"
	)
	parser.add_argument(
		"-d", "--dev", help="Setup Development System", action="store_true"
	)
	parser.add_argument(
		"-s",
		"--sitename",
		help="Site Name(s) for your production bench",
		default=[],
		action="append",
		dest="sites",
	)
	parser.add_argument("-n", "--project", help="Project Name", default="frappe")
	parser.add_argument("-i", "--image", help="Full Image Name")
	parser.add_argument(
		"--email", help="Add email for the SSL.", required="--prod" in sys.argv
	)
	parser.add_argument(
		"-v", "--version", help="ERPNext version to install, defaults to latest stable"
	)
	args = parser.parse_args()
	if args.dev:
		cprint("\nSetting Up Development Instance\n", level=2)
		logging.info("Running Development Setup")
		setup_dev_instance(args.project)
	elif args.prod:
		cprint("\nSetting Up Production Instance\n", level=2)
		logging.info("Running Production Setup")
		if "example.com" in args.email:
			cprint("Emails with example.com not acceptable", level=1)
			sys.exit(1)
		setup_prod(args.project, args.sites, args.email, args.version, args.image)
	else:
		parser.print_help()
