# rfpkg bash completion

_rfpkg()
{
    COMPREPLY=()

    in_array()
    {
        local i
        for i in $2; do
            [[ $i = $1 ]] && return 0
        done
        return 1
    }

    _filedir_exclude_paths()
    {
        _filedir "$@"
        for ((i=0; i<=${#COMPREPLY[@]}; i++)); do
            [[ ${COMPREPLY[$i]} =~ /?\.git/? ]] && unset COMPREPLY[$i]
        done
    }

    local cur prev
    _get_comp_words_by_ref cur prev

    # global options

    local options="--help -v -q"
    local options_value="--release --user --path --user-config --name --namespace"
    local commands="build chain-build ci clean clog clone co commit compile \
    container-build diff gimmespec giturl help gitbuildhash import install lint \
    local mockbuild mock-config module-build module-build-cancel \
    module-build-local module-build-info module-build-watch module-overview \
    module-scratch-build \
    new new-sources patch prep pull push retire request-branch request-repo \
    request-tests-repo request-side-tag list-side-tags remove-side-tag \
    scratch-build set-distgit-token set-pagure-token sources srpm switch-branch \
    tag unused-patches update upload \
    verify-files verrel override fork"

    # parse main options and get command

    local command=
    local command_first=
    local path=

    local i w
    for (( i = 0; i < ${#COMP_WORDS[*]} - 1; i++ )); do
        w="${COMP_WORDS[$i]}"
        # option
        if [[ ${w:0:1} = - ]]; then
            if in_array "$w" "$options_value"; then
                ((i++))
                [[ "$w" = --path ]] && path="${COMP_WORDS[$i]}"
            fi
        # command
        elif in_array "$w" "$commands"; then
            command="$w"
            command_first=$((i+1))
            break
        fi
    done

    # complete base options

    if [[ -z $command ]]; then
        if [[ $cur == -* ]]; then
            COMPREPLY=( $(compgen -W "$options $options_value" -- "$cur") )
            return 0
        fi

        case "$prev" in
            --release | --user | -u | --config)
                ;;
            --path)
                _filedir_exclude_paths
                ;;
            --namespace)
                COMPREPLY=( $(compgen -W "$(_rfpkg_namespaces)" -- "$cur") )
                ;;
            *)
                COMPREPLY=( $(compgen -W "$commands" -- "$cur") )
                ;;
        esac

        return 0
    fi

    # parse command specific options

    local options=
    local options_target= options_arches= options_branch= options_string= options_file= options_dir= options_srpm= options_mroot= options_builder= options_namespace=
    local options_update_type= options_update_request=
    local options_yaml=
    local after= after_more=

    case $command in
        help|gimmespec|gitbuildhash|giturl|new|push|unused-patches|verrel|set-distgit-token|set-pagure-token)
            ;;
        build)
            options="--nowait --background --skip-tag --scratch --skip-remote-rules-validation --fail-fast"
            options_arches="--arches"
            options_srpm="--srpm"
            options_target="--target"
            ;;
        chain-build)
            options="--nowait --background"
            options_target="--target"
            after="package"
            after_more=true
            ;;
        clean)
            options="--dry-run -x"
            ;;
        clog)
            options="--raw"
            ;;
        clone|co)
            options="--branches --anonymous"
            options_branch="-b"
            after="package"
            ;;
        commit|ci)
            options="--push --clog --raw --tag --with-changelog"
            options_string="--message"
            options_file="--file"
            after="file"
            after_more=true
            ;;
        compile|install)
            options="--short-circuit"
            options_arches="--arch"
            options_dir="--builddir"
            ;;
        container-build)
            options="--scratch --nowait --repo-url --skip-remote-rules-validation"
            options_arches="--arches"
            options_target="--target"
            ;;
        diff)
            options="--cached"
            after="file"
            after_more=true
            ;;
        import)
            options="--create"
            options_branch="--branch"
            after="srpm"
            ;;
        lint)
            options="--info"
            options_file="--rpmlintconf"
            ;;
        list-side-tags)
            options="--mine"
            options_string="--user --base-tag"
            ;;
        local)
            options="--md5"
            options_arches="--arch"
            options_string="--with --without"
            options_dir="--builddir"
            ;;
        mock-config)
            options="--target"
            options_arches="--arch"
            ;;
        mockbuild)
            options="--md5 --no-clean --no-cleanup-after --no-clean-all --shell"
            options_string="--with --without"
            options_mroot="--root --mock-config"
            ;;
        module-build)
            options="--scratch --watch"
            options_string="--optional --requires --buildrequires"
            options_yaml="--file"
            options_srpm="--srpm"
            ;;
        module-build-local)
            options="--skip-tests"
            options_string="--add-local-build --stream --set-default-stream"
            options_yaml="--file"
            options_srpm="--srpm"
            ;;
        module-overview)
            options="--unfinished"
            options_string="--limit"
            ;;
        module-scratch-build)
            options="--watch"
            options_string="--optional --requires --buildrequires"
            options_yaml="--file"
            options_srpm="--srpm"
            ;;
        patch)
            options="--rediff"
            options_string="--suffix"
            ;;
        prep|verify-files)
            options_arches="--arch"
            options_dir="--builddir"
            ;;
        pull)
            options="--rebase --no-rebase"
            ;;
        remove-side-tag)
            after_more=true
            ;;
        retire)
            after_more=true
            ;;
        request-branch)
            options="--no-git-branch --all-releases --no-auto-module"
            options_string="--sl --repo"
            ;;
        request-repo)
            options="--exception --no-initial-commit"
            options_string="--description --monitor --upstreamurl --summary"
            options_namespace="--namespace"
            ;;
        request-tests-repo)
            options_string="--bug"
            ;;
        request-side-tag)
            options_string="--base-tag"
            ;;
        scratch-build)
            options="--nowait --background"
            options_target="--target"
            options_arches="--arches"
            options_srpm="--srpm"
            ;;
        sources)
            options_dir="--outdir"
            ;;
        srpm)
            options="--md5"
            ;;
        switch-branch)
            options="--list"
            after="branch"
            ;;
        tag)
            options="--clog --raw --force --list --delete"
            options_string="--message"
            options_file="--file"
            after_more=true
            ;;
        upload|new-sources)
            after="file"
            after_more=true
            ;;
        update)
            options="--not-close-bugs --suggest-reboot --disable-autokarma"
            options_string="--notes --bugs --stable-karma --unstable-karma"
            options_update_type="--type"
            options_update_request="--request"
            ;;
    esac

    local all_options="--help $options"
    local all_options_value="$options_target $options_arches $options_branch \
    $options_string $options_file $options_dir $options_srpm $options_mroot \
    $options_builder $options_namespace $options_update_type $options_update_request \
    $options_yaml"

    # count non-option parameters

    local i w
    local last_option=
    local after_counter=0
    for (( i = $command_first; i < ${#COMP_WORDS[*]} - 1; i++)); do
        w="${COMP_WORDS[$i]}"
        if [[ ${w:0:1} = - ]]; then
            if in_array "$w" "$all_options"; then
                last_option="$w"
                continue
            elif in_array "$w" "$all_options_value"; then
                last_option="$w"
                ((i++))
                continue
            fi
        fi
        in_array "$last_option" "$options_arches" || ((after_counter++))
    done

    # completion

    if [[ -n $options_target ]] && in_array "$prev" "$options_target"; then
        COMPREPLY=( $(compgen -W "$(_rfpkg_target)" -- "$cur") )

    elif [[ -n $options_arches ]] && in_array "$last_option" "$options_arches"; then
        COMPREPLY=( $(compgen -W "$(_rfpkg_arch) $all_options" -- "$cur") )

    elif [[ -n $options_srpm ]] && in_array "$prev" "$options_srpm"; then
        _filedir_exclude_paths "*.src.rpm"

    elif [[ -n $options_yaml ]] && in_array "$prev" "$options_yaml"; then
        _filedir_exclude_paths "yaml"

    elif [[ -n $options_branch ]] && in_array "$prev" "$options_branch"; then
        COMPREPLY=( $(compgen -W "$(_rfpkg_branch "$path")" -- "$cur") )

    elif [[ -n $options_file ]] && in_array "$prev" "$options_file"; then
        _filedir_exclude_paths

    elif [[ -n $options_dir ]] && in_array "$prev" "$options_dir"; then
        _filedir_exclude_paths -d

    elif [[ -n $options_string ]] && in_array "$prev" "$options_string"; then
        COMPREPLY=( )

    elif [[ -n $options_mroot ]] && in_array "$prev" "$options_mroot"; then
        COMPREPLY=( )
        if declare -F _mock_root &>/dev/null; then
            _mock_root
        elif declare -F _xfunc &>/dev/null; then
            _xfunc mock _mock_root
        fi

    elif [[ -n $options_namespace ]] && in_array "$prev" "$options_namespace"; then
        COMPREPLY=( $(compgen -W "$(_rfpkg_namespaces)" -- "$cur") )

    elif [[ -n $options_update_type ]] && in_array "$prev" "$options_update_type"; then
        COMPREPLY=( $(compgen -W "bugfix security enhancement newpackage" -- "$cur") )

    elif [[ -n $options_update_request ]] && in_array "$prev" "$options_update_request"; then
        COMPREPLY=( $(compgen -W "testing stable" -- "$cur") )

    else
        local after_options=

        if [[ $after_counter -eq 0 ]] || [[ $after_more = true ]]; then
            case $after in
                file)    _filedir_exclude_paths ;;
                srpm)    _filedir_exclude_paths "*.src.rpm" ;;
                branch)  after_options="$(_rfpkg_branch "$path")" ;;
                package) after_options="$(_rfpkg_package "$cur")";;
            esac
        fi

        if [[ $cur != -* ]]; then
            all_options=
            all_options_value=
        fi

        COMPREPLY+=( $(compgen -W "$all_options $all_options_value $after_options" -- "$cur" ) )
    fi

    return 0
} &&
complete -F _rfpkg rfpkg

_rfpkg_target()
{
    koji list-targets --quiet 2>/dev/null | cut -d" " -f1
}

_rfpkg_arch()
{
    echo "i386 i686 x86_64 armv5tel armv7hl armv7hnl ppc ppc64 ppc64le ppc64p7 s390 s390x"
}

_rfpkg_branch()
{
    local git_options= format="--format %(refname:short)"
    [[ -n $1 ]] && git_options="--git-dir=$1/.git"

    git $git_options for-each-ref $format 'refs/remotes' | sed 's,.*/,,'
    git $git_options for-each-ref $format 'refs/heads'
}

_rfpkg_package()
{
    repoquery -C --qf=%{sourcerpm} "$1*" 2>/dev/null | sort -u | sed -r 's/(-[^-]*){2}\.src\.rpm$//'
}

_rfpkg_namespaces()
{
    grep "^distgit_namespaces =" /etc/rpkg/rfpkg.conf | cut -d'=' -f2
}


# Local variables:
# mode: shell-script
# sh-basic-offset: 4
# sh-indent-comment: t
# indent-tabs-mode: nil
# End:
# ex: ts=4 sw=4 et filetype=sh