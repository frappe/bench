_bench_completion() {
    # Complete commands using click bashcomplete
    COMPREPLY=( $( COMP_WORDS="${COMP_WORDS[*]}" \
                   COMP_CWORD=$COMP_CWORD \
                   _BENCH_COMPLETE=complete $1 ) )
    if [ -d "sites" ]; then
        # Also add frappe commands if present

        # bench_helper.py expects to be executed from "sites" directory
        cd sites

        # All frappe commands are subcommands under "bench frappe"
        # Frappe is only installed in virtualenv "env" so use appropriate python executable
        COMPREPLY+=( $( COMP_WORDS="bench frappe "${COMP_WORDS[@]:1} \
                        COMP_CWORD=$(($COMP_CWORD+1)) \
                        _BENCH_COMPLETE=complete ../env/bin/python ../apps/frappe/frappe/utils/bench_helper.py ) )

        # If the word before the current cursor position in command typed so far is "--site" then only list sites
        if [ ${COMP_WORDS[COMP_CWORD-1]} == "--site" ]; then
            COMPREPLY=( $( ls -d ./*/site_config.json | cut -f 2 -d "/" | xargs echo ) )
        fi

        # Get out of sites directory now
        cd ..
    fi
    return 0
}

# Only support bash and zsh
if [ -n "$BASH" ] ; then
    complete -F _bench_completion -o default bench;
elif [ -n "$ZSH_VERSION" ]; then
    # Use zsh in bash compatibility mode
    autoload bashcompinit
    bashcompinit
    complete -F _bench_completion -o default bench;
fi
