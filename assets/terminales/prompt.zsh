autoload -Uz compinit add-zsh-hook
compinit
bindkey -e
zmodload zsh/datetime
unsetopt PROMPT_SUBST

HISTFILE="$ZDOTDIR/history"
HISTSIZE=10000
SAVEHIST=10000
setopt APPEND_HISTORY HIST_IGNORE_DUPS

export LS_COLORS="${LS_COLORS:+$LS_COLORS:}di=38;2;177;132;237"
alias ls='ls --color=auto'

eva01_reloj() {
    local cabeza fecha linea
    local -i ancho
    cabeza="${USER}@${HOST%%.*} ${(%):-%~}"
    strftime -s fecha '[%a %d/%m %H:%M:%S]' "$EPOCHSECONDS"
    ancho=$(( COLUMNS - ${#cabeza} - ${#fecha} ))
    (( ancho < 1 )) && ancho=1
    linea="${(l:$ancho::─:)}"
    cabeza="${cabeza//\%/%%}"
    fecha="${fecha//\%/%%}"
    PROMPT="%F{#B7FF3C}${cabeza}%F{#B184ED}${linea}%F{#B7FF3C}${fecha}%f"$'\n'"%F{#B7FF3C}❯ %f"
    RPROMPT=''
}

TRAPALRM() {
    if zle; then
        eva01_reloj
        zle reset-prompt
    fi
    return 0
}

TMOUT=1
add-zsh-hook precmd eva01_reloj
