import os
import importlib


def run(bench_path):
	source_patch_file = os.path.join(
		os.path.dirname(os.path.abspath(__file__)), "patches.txt"
	)
	target_patch_file = os.path.join(os.path.abspath(bench_path), "patches.txt")

	with open(source_patch_file) as f:
		patches = [
			p.strip()
			for p in f.read().splitlines()
			if p.strip() and not p.strip().startswith("#")
		]

	executed_patches = []
	if os.path.exists(target_patch_file):
		with open(target_patch_file) as f:
			executed_patches = f.read().splitlines()

	try:
		for patch in patches:
			if patch not in executed_patches:
				module = importlib.import_module(patch.split()[0])
				execute = getattr(module, "execute")
				result = execute(bench_path)

				if not result:
					executed_patches.append(patch)

	finally:
		with open(target_patch_file, "w") as f:
			f.write("\n".join(executed_patches))

			# end with an empty line
			f.write("\n")
