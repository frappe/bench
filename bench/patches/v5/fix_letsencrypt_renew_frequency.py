from bench.config.common_site_config import get_config
from crontab import CronTab


def execute(bench_path):
	"""
		This patch fixes a cron job that would renew letsencrypt certificate
	"""

	job_command = '/opt/certbot-auto renew --force-renewal -a nginx --post-hook "systemctl reload nginx"'
	system_crontab = CronTab(user='root')
	job_comment = "Renew lets-encrypt every month"

	for job in system_crontab.find_comment(job_comment)
		system_crontab.remove(job)
		job = system_crontab.new(command=job_command, comment=job_comment)
		job.setall('0 0 1 * *') # Run at 00:00 on every day-of-month 1
		system_crontab.write()
		break
