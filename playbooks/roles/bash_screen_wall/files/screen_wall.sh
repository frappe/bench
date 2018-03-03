if [ $TERM != 'screen' ]
then
        PS1='HEY! USE SCREEN '$PS1
fi

sw() {
        screen -x $1 || screen -S $1
}
