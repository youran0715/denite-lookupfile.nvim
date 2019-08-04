au BufEnter * call denite#sources#lookupfile#buf_enter()
au VimEnter * call denite#sources#lookupfile#vim_enter()
au VimLeave * call denite#sources#lookupfile#vim_leave()
command! MruClean :call denite#sources#lookupfile#clean_mru()
