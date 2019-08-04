let s:plugin_path = escape(expand('<sfile>:p:h'), '\')
execute 'py3file ' . s:plugin_path . '/lookupfile.py'

function! s:get_cache_dir()
	set shellslash
    let cache_dir = expand($HOME) . "/.cache/vim/lookupfile/"

	let cwd = substitute(getcwd(), '/', '_', 'g')
	let cwd = substitute(cwd, ':', '_', 'g')
	let dir = cache_dir . cwd . '/'

    if !isdirectory(dir)
        call mkdir(dir, "p")
    endif

	if g:is_os_windows
		set noshellslash
	endif

    return dir
endfunction

function! s:get_cache_path_mrulist()
    return s:get_cache_dir() . 'mrulist5'
endfunction

let s:is_inited = 0
function! denite#sources#lookupfile#vim_enter()
    echo "vim_enter"
    if !s:is_inited
        let s:file_path = s:get_cache_path_mrulist()
        if filereadable(s:file_path)
            execute 'python3 UnitePyLoadMrus()'
        endif
        let s:is_inited = 1
    endif
endfunction

function! denite#sources#lookupfile#clean_mru()
    execute 'python3 UnitePyCleanMrus()'
endfunction

function! denite#sources#lookupfile#vim_leave()
    let s:file_path = s:get_cache_path_mrulist()
    execute 'python3 UnitePySaveMrus()'
endfunction

function! denite#sources#lookupfile#buf_enter()
    let s:buf_path = bufname("%")
    if !filereadable(s:buf_path)
        return
    endif

    execute 'python3 UnitePyAddMru()'
endfunction

function! denite#sources#lookupfile#mrus()
    let s:mrus = []
    execute 'python3 UnitePyGetMrus()'
    return s:mrus
endfunction
