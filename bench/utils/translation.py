# imports - standard imports
import itertools
import json
import os


def update_translations_p(args):
	import requests

	try:
		update_translations(*args)
	except requests.exceptions.HTTPError:
		print("Download failed for", args[0], args[1])


def download_translations_p():
	import multiprocessing

	pool = multiprocessing.Pool(multiprocessing.cpu_count())

	langs = get_langs()
	apps = ("frappe", "erpnext")
	args = list(itertools.product(apps, langs))

	pool.map(update_translations_p, args)


def download_translations():
	langs = get_langs()
	apps = ("frappe", "erpnext")
	for app, lang in itertools.product(apps, langs):
		update_translations(app, lang)


def get_langs():
	lang_file = "apps/frappe/frappe/geo/languages.json"
	with open(lang_file) as f:
		langs = json.loads(f.read())
	return [d["code"] for d in langs]


def update_translations(app, lang):
	import requests

	translations_dir = os.path.join("apps", app, app, "translations")
	csv_file = os.path.join(translations_dir, f"{lang}.csv")
	url = f"https://translate.erpnext.com/files/{app}-{lang}.csv"
	r = requests.get(url, stream=True)
	r.raise_for_status()

	with open(csv_file, "wb") as f:
		for chunk in r.iter_content(chunk_size=1024):
			# filter out keep-alive new chunks
			if chunk:
				f.write(chunk)
				f.flush()

	print("downloaded for", app, lang)
