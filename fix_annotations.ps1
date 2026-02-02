# Mass fix: Add "from __future__ import annotations" to all Python files that need it

$files = Get-ChildItem -Path . -Recurse -Include *.py | Where-Object {
    $content = Get-Content $_.FullName -Raw
    # Check if file uses typing and doesn't already have the future import
    ($content -match 'from typing import|import typing') -and 
    ($content -notmatch 'from __future__ import annotations')
}

$count = 0
foreach ($file in $files) {
    Write-Host "Fixing: $($file.FullName)"
    
    $content = Get-Content $file.FullName -Raw
    
    # Find the first import or the docstring end
    if ($content -match '(?ms)^(""".*?"""\s*\n|' + "'''.*?'''\s*\n" + '|)(.*?)$') {
        $docstring = $matches[1]
        $rest = $matches[2]
        
        # Add the future import after docstring, before other imports
        $newContent = $docstring + "from __future__ import annotations`n`n" + $rest
        
        Set-Content -Path $file.FullName -Value $newContent -NoNewline
        $count++
    }
}

Write-Host "`nFixed $count files"
