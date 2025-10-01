vim9script

# run the main python file
:noremap <leader>m :update<CR>:ScratchTermReplaceU .venv/Scripts/python.exe src/unit_track_content_changes/main.py<CR>
