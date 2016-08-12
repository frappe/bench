import bench, os, click, errno, urllib
from bench.utils import exec_cmd, CommandFailedError
from bench.config.site_config import update_site_config, remove_domain, get_domains
from bench.config.nginx import make_nginx_conf
from bench.config.production_setup import service
from bench.config.common_site_config import get_config
from crontab import CronTab

def setup_letsencrypt(site, custom_domain, bench_path):

	site_path = os.path.join(bench_path, "sites", site, "site_config.json")
	if not os.path.exists(os.path.dirname(site_path)):
		print "No site named "+site
		return

	if custom_domain:
		domains = get_domains(site, bench_path)
		for d in domains:
			if (isinstance(d, dict) and d['domain']==custom_domain):
				print "SSL for Domain {0} already exists".format(custom_domain)
				return

		if not custom_domain in domains:
			print "No custom domain named {0} set for site".format(custom_domain)
			return

	click.confirm('Running this will stop the nginx service temporarily causing your sites to go offline\n'
		'Do you want to continue?',
		abort=True)

	if not get_config(bench_path).get("dns_multitenant"):
		print "You cannot setup SSL without DNS Multitenancy"
		return

	create_config(site, custom_domain)
	run_certbot_and_setup_ssl(site, custom_domain, bench_path)
	setup_crontab()


def create_config(site, custom_domain):
	config = bench.env.get_template('letsencrypt.cfg').render(domain=custom_domain or site)
	config_path = '/etc/letsencrypt/configs/{site}.cfg'.format(site=custom_domain or site)
	create_dir_if_missing(config_path)

	with open(config_path, 'w') as f:
		f.write(config)


def run_certbot_and_setup_ssl(site, custom_domain, bench_path):
	service('nginx', 'stop')
	get_certbot()

	try:
		exec_cmd("{path} --config /etc/letsencrypt/configs/{site}.cfg certonly".format(path=get_certbot_path(), site=custom_domain or site))
	except CommandFailedError:
		service('nginx', 'start')
		print "There was a problem trying to setup SSL for your site"
		return

	ssl_path = "/etc/letsencrypt/live/{site}/".format(site=custom_domain or site)
	ssl_config = { "ssl_certificate": os.path.join(ssl_path, "fullchain.pem"),
					"ssl_certificate_key": os.path.join(ssl_path, "privkey.pem") }

	if custom_domain:
		remove_domain(site, custom_domain, bench_path)
		domains = get_domains(site, bench_path)
		ssl_config['domain'] = custom_domain		
		domains.append(ssl_config)
		update_site_config(site, { "domains": domains }, bench_path=bench_path)
	else:
		update_site_config(site, ssl_config, bench_path=bench_path)
	
	make_nginx_conf(bench_path)
	service('nginx', 'start')


def setup_crontab():
	job_command = 'sudo service nginx stop && /opt/certbot-auto renew && sudo service nginx start'
	user_crontab = CronTab(user=True)
	if job_command not in str(user_crontab):
		job  = user_crontab.new(command=job_command, comment="Renew lets-encrypt every month")
		job.every().month()
		job.enable()
		user_crontab.write()


def create_dir_if_missing(path):
	if not os.path.exists(os.path.dirname(path)):
		os.makedirs(os.path.dirname(path))


def get_certbot():
	certbot_path = get_certbot_path()
	create_dir_if_missing(certbot_path)

	if not os.path.isfile(certbot_path):
		urllib.urlretrieve ("https://dl.eff.org/certbot-auto", certbot_path)
		os.chmod(certbot_path, 0744)


def get_certbot_path():
	return "/opt/certbot-auto"


def renew_certs():
	click.confirm('Running this will stop the nginx service temporarily causing your sites to go offline\n'
		'Do you want to continue?',
		abort=True)

	service('nginx', 'stop')
	exec_cmd("{path} renew".format(path=get_certbot_path()))
	service('nginx', 'start')
