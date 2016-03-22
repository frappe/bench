import click

@click.group()
def setup():
	"Setup bench"
	pass


@click.command('sudoers')
@click.argument('user')
def setup_sudoers(user):
	"Add commands to sudoers list for execution without password"
	from bench.utils import setup_sudoers
	setup_sudoers(user)


@click.command('nginx')
def setup_nginx():
	"generate config for nginx"
	from bench.config.nginx import make_nginx_conf
	make_nginx_conf(bench_path=".")


@click.command('supervisor')
def setup_supervisor():
	"generate config for supervisor"
	from bench.config.supervisor import generate_supervisor_config
	generate_supervisor_config(bench_path=".")


@click.command('redis')
def setup_redis():
	"generate config for redis cache"
	from bench.config.redis import generate_config
	generate_config('.')


@click.command('production')
@click.argument('user')
def setup_production(user):
	"setup bench for production"
	from bench.config.production_setup import setup_production
	setup_production(user=user)


@click.command('auto-update')
def setup_auto_update():
	"Add cronjob for bench auto update"
	from bench.utils import setup_auto_update
	setup_auto_update()


@click.command('backups')
def setup_backups():
	"Add cronjob for bench backups"
	from bench.utils import setup_backups
	setup_backups()

@click.command('env')
def setup_env():
	"Setup virtualenv for bench"
	from bench.utils import setup_env
	setup_env()


@click.command('procfile')
def setup_procfile():
	"Setup Procfile for bench start"
	from bench.config.procfile import setup_procfile
	setup_procfile('.')


@click.command('socketio')
def setup_socketio():
	"Setup node deps for socketio server"
	from bench.utils import setup_socketio
	setup_socketio()


@click.command('config')
def setup_config():
	"overwrite or make config.json"
	from bench.config.common_site_config import make_config
	make_config('.')


setup.add_command(setup_sudoers)
setup.add_command(setup_nginx)
setup.add_command(setup_supervisor)
setup.add_command(setup_redis)
setup.add_command(setup_production)
setup.add_command(setup_auto_update)
setup.add_command(setup_backups)
setup.add_command(setup_env)
setup.add_command(setup_procfile)
setup.add_command(setup_socketio)
setup.add_command(setup_config)
