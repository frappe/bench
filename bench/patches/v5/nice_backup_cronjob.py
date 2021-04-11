from bench.config.common_site_config import get_config
from bench.utils import which
from crontab import CronTab


def execute(bench_path):
	"""
		This patch gives the backup cron job a lower priority
	"""

	nice = which("nice")
	if not nice:
		return

	user = get_config(bench_path=bench_path).get('frappe_user')
	user_crontab = CronTab(user=user)

	for job in user_crontab.find_comment("bench auto backups set for every 6 hours"):
		if nice not in job.command:
			job.command = job.command.replace("&& ", "&& {} ".format(nice))

		user_crontab.write()
