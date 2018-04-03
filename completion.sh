_setup_bench_tab_completion () {
	if [ -n "$BASH" ] ; then
        _bench () {
			local cur=${COMP_WORDS[COMP_CWORD]}
			local prev=${COMP_WORDS[COMP_CWORD-1]}
			if [[ $prev == "--site" ]]; then
				COMPREPLY=( $(compgen -W "`_site_dirs`" -- $cur) )
			fi
			}
			complete -F _bench bench
	elif [ -n "$ZSH_VERSION" ]; then
		 _bench () {
			 local a
			 local prev
			 read -l a
			 prev=`echo $a| awk '{ print $NF }'`
			 if [[ $prev == "--site" ]]; then
				 reply=($(_site_dirs))
			 fi
         }
		 compctl -K _bench bench
	fi
}

_site_dirs() {
	ls -d sites/*/ | sed "s/sites\///g" | sed "s/\/$//g" | xargs echo
}


_setup_bench_tab_completion
