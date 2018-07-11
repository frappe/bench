_setup_bench_tab_completion () {
	if [ -n "$BASH" ] ; then
		eval "$(_BENCH_COMPLETE=source bench)"
	elif [ -n "$ZSH_VERSION" ]; then
		autoload bashcompinit
		bashcompinit
		eval "$(_BENCH_COMPLETE=source bench)"
	fi
}

_setup_bench_tab_completion
