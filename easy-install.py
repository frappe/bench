#!/usr/bin/env python3
import argparse
import subprocess
import os
import sys
import time
from shutil import which
import platform
from secrets import token_bytes
from base64 import b64encode

CRED = "\033[31m"
CEND = "\033[0m"
CGRN = "\33[92m"
CYLW = "\33[93m"


def clone_frappe_docker_repo() -> None:
    try:
        subprocess.run(
            ["git", "clone", "https://github.com/frappe/frappe_docker"], check=True
        )
    except Exception as e:
        print(f"\n{CRED}Cloning frappe_docker Failed{CEND}\n\n", e)


def write_to_env(wd, site,db_pass,email):
    site_name = site if site != "" else ""
    with open(os.path.join(wd, ".env"), "w") as f:
        f.writelines(
            [
                "FRAPPE_VERSION=v14.17.1\n",
                "ERPNEXT_VERSION=v14.9.0\n",
                f"DB_PASSWORD={db_pass}\n",
                "DB_HOST=db\n",
                "DB_PORT=3306\n",
                "REDIS_CACHE=redis-cache:6379\n",
                "REDIS_QUEUE=redis-queue:6379\n",
                "REDIS_SOCKETIO=redis-socketio:6379\n",
                f"LETSENCRYPT_EMAIL={email}\n"
                f"FRAPPE_SITE_NAME_HEADER={site_name}",
            ]
        )

def generate_pass(length:int=9) -> str:
    return b64encode(token_bytes(length)).decode()
    

def check_repo_exists() -> bool:
    return os.path.exists(os.path.join(os.getcwd(), "frappe_docker"))


def setup_prod(project: str, sitename: str,email:str):
    if check_repo_exists():
        compose_file_name = os.path.join(os.path.expanduser("~"), f"{project}-compose.yml")
        docker_repo_path = os.path.join(os.getcwd(), "frappe_docker")
        admin_pass = generate_pass()
        db_pass = generate_pass(6)
        print(
            f"\n{CYLW}Please refer to .example.env file in the frappe_docker folder to know which keys to set{CEND}\n\n"
        )
        with open(compose_file_name, "w") as f:
            if not os.path.exists(os.path.join(docker_repo_path, "/.env")):
                write_to_env(docker_repo_path, sitename,db_pass,email)
                print(
                    f"\n{CYLW}A .env file is generated with basic configs. Please edit it to fit your needs {CEND}\n"
                )
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
                        "overrides/compose.erpnext.yaml",
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

            except Exception as e:
                print(f"\n{CRED}Generating Compose File failed{CEND}\n")
        try:
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
            
        except Exception as e:
            print(
                f"{CRED} Docker Compose failed, please check the container logs{CEND}\n",
                e,
            )
        print(f"\n{CGRN}Creating site: {sitename} {CEND}\n")
        with open(os.path.join(os.path.expanduser("~"),"passwords.txt"),"w") as f:
            f.writelines(f"Administrator:{admin_pass}\n")
            f.writelines(f"MariaDB Root Password:{db_pass}\n")
        try:
            subprocess.run([
                which("docker"),"compose",
                "-p",project,"exec","backend",
                "bench","new-site",sitename,
                "--db-root-password",db_pass,
                "--admin-password",admin_pass,
                "--install-app","erpnext"
                ],check=True)
        except Exception as e:
            print(
                f"{CRED} Bench Site creation failed{CEND}\n",
                e,
            )
    else:
        install_docker()
        clone_frappe_docker_repo()
        setup_prod(project, sitename,email)  # Recursive


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
            print(
                f"{CYLW}Please go through the Development Documentation: https://github.com/frappe/frappe_docker/tree/main/development to fully complete the setup.{CEND}"
            )
        except Exception as e:
            print(f"{CRED}Setting Up Development Environment Failed\n{CEND}", e)
    else:
        install_docker()
        clone_frappe_docker_repo()
        setup_dev_instance(project)  # Recursion on goes brrrr


def install_docker():
    if which("docker") is None:
        print(f"{CGRN}Docker is not installed, Installing Docker...{CEND}")
        if platform.system() == "Darwin" or platform.system() == "Windows":
            print(
                f"""{CRED}
                This script doesn't install Docker on {"Mac" if platform.system()=="Darwin" else "Windows"}.

                Please go through the Docker Installation docs for your system and run this script again{CEND}"""
            )
            exit(1)
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
            print(f"{CYLW}Waiting Docker to start{CEND}")
            time.sleep(10)
            subprocess.run(
                ["sudo", "systemctl", "restart", "docker.service"], check=True
            )
        except Exception as e:
            print(f"{CRED}Failed to Install Docker{CYLW}\n", e)
            print(
                f"\n\n {CYLW}Try Installing Docker Manually and re-run this script again{CEND}\n\n"
            )
            exit(1)
    else:
        return


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
        help="The Site Name for your production site",
        default="site1.local",
    )
    parser.add_argument(
        "-n",
        "--project",
        help="Project Name",
        default="frappe",
    )
    parser.add_argument(
        "--email",
        help="Add email for the SSL.",
        required="--prod" in sys.argv
    )
    args = parser.parse_args()
    if args.dev:
        print(f"\n{CGRN}Setting Up Development Instance{CEND}\n")
        setup_dev_instance(args.project)
    elif args.prod:
        print(f"\n{CGRN}Setting Up Production Instance{CEND}\n")
        if "example.com" in args.email:
            print(f"{CRED} Emails with example.com not acceptable{CEND}")
        setup_prod(args.project, args.sitename, args.email)