$root = (Resolve-Path '.\docs').Path
$htmlFiles = Get-ChildItem $root -Recurse -Filter '*.html' -File
$issues = New-Object System.Collections.ArrayList

foreach ($file in $htmlFiles) {
  $content = [IO.File]::ReadAllText($file.FullName)
  $matches = [regex]::Matches($content, '(?i)(href|src)=["''][^"'']+["'']')

  foreach ($m in $matches) {
    $pair = $m.Value -replace '^(?i)(href|src)=["'']', '' -replace '["'']$', ''

    if ($pair -match '^(mailto:|tel:|javascript:|data:)') { continue }

    if ($pair -match '^https?://retro\.caracore\.com\.br') {
      $pair = $pair -replace '^https?://retro\.caracore\.com\.br', ''
    } elseif ($pair -match '^https?://') {
      continue
    }

    $parts = $pair.Split('#')
    $path = $parts[0]
    $anchor = if ($parts.Count -gt 1) { $parts[1] } else { '' }

    if ($path -eq '') {
      $target = $file.FullName
    } elseif ($path.StartsWith('/')) {
      $target = Join-Path $root ($path.TrimStart('/') -replace '/', '\')
    } else {
      $target = Join-Path $file.DirectoryName ($path -replace '/', '\')
    }

    $resolved = $null
    if (Test-Path $target -PathType Leaf) {
      $resolved = $target
    } elseif (Test-Path $target -PathType Container) {
      $idx = Join-Path $target 'index.html'
      if (Test-Path $idx -PathType Leaf) { $resolved = $idx }
    } elseif ([IO.Path]::GetExtension($target) -eq '') {
      $idx = Join-Path $target 'index.html'
      $html = $target + '.html'
      if (Test-Path $idx -PathType Leaf) {
        $resolved = $idx
      } elseif (Test-Path $html -PathType Leaf) {
        $resolved = $html
      }
    }

    if (-not $resolved) {
      [void]$issues.Add([pscustomobject]@{
        Type = 'missing-target'
        File = $file.FullName
        Link = $pair
        Detail = $target
      })
      continue
    }

    if ($anchor -and [IO.Path]::GetExtension($resolved).ToLower() -eq '.html') {
      $targetContent = [IO.File]::ReadAllText($resolved)
      $anchorPattern = '(?i)id=["'']' + [regex]::Escape($anchor) + '["'']|name=["'']' + [regex]::Escape($anchor) + '["'']'
      if ($targetContent -notmatch $anchorPattern) {
        [void]$issues.Add([pscustomobject]@{
          Type = 'missing-anchor'
          File = $file.FullName
          Link = $pair
          Detail = $resolved
        })
      }
    }
  }
}

Write-Output ('ISSUE_COUNT=' + $issues.Count)
$issues | Group-Object Type | ForEach-Object {
  Write-Output ('TYPE=' + $_.Name + ';COUNT=' + $_.Count)
}
$issues | Select-Object -First 80 | ForEach-Object {
  Write-Output ('[' + $_.Type + '] ' + $_.File + ' => ' + $_.Link + ' --> ' + $_.Detail)
}
