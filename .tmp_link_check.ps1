$root=(Resolve-Path 'docs').Path
$files=Get-ChildItem -Path $root -Recurse -File -Include *.html,*.htm
$rx='(?is)(?:href|src)\s*=\s*["'']([^"'']+)["'']'

function Resolve-LinkPath($sourceDir,$clean,$rootPath){
  if($clean.StartsWith('/')){ return Join-Path $rootPath ($clean.TrimStart('/').Replace('/','\\')) }
  return Join-Path $sourceDir ($clean.Replace('/','\\'))
}

function Test-ExactCasePath($fullPath){
  if(-not (Test-Path -LiteralPath $fullPath)){ return $false }
  $parts = $fullPath -split '\\'
  if($parts.Length -lt 2){ return $true }
  $cursor = $parts[0]
  for($i=1; $i -lt $parts.Length; $i++){
    $name = $parts[$i]
    if([string]::IsNullOrWhiteSpace($name)){ continue }
    $children = Get-ChildItem -LiteralPath ($cursor + '\\') -Force -ErrorAction SilentlyContinue
    if(-not $children){ return $false }
    $exact = $children | Where-Object { $_.Name -ceq $name } | Select-Object -First 1
    if(-not $exact){ return $false }
    $cursor = Join-Path $cursor $name
  }
  return $true
}

$broken = New-Object System.Collections.Generic.List[object]
$caseIssues = New-Object System.Collections.Generic.List[object]

foreach($file in $files){
  $content=[System.IO.File]::ReadAllText($file.FullName,[System.Text.Encoding]::UTF8)
  foreach($m in [regex]::Matches($content,$rx)){
    $raw=$m.Groups[1].Value
    if([string]::IsNullOrWhiteSpace($raw)){ continue }
    if($raw -match '^(mailto:|tel:|javascript:|data:|https?://|//)'){ continue }
    if($raw.StartsWith('#')){ continue }
    $clean=$raw -replace '[?#].*$',''
    if([string]::IsNullOrWhiteSpace($clean)){ continue }

    $target=Resolve-LinkPath -sourceDir $file.DirectoryName -clean $clean -rootPath $root
    $exists=Test-Path -LiteralPath $target
    if(-not $exists -and -not [System.IO.Path]::HasExtension($target)){
      $idxHtml=Join-Path $target 'index.html'
      $idxHtm=Join-Path $target 'index.htm'
      if(Test-Path -LiteralPath $idxHtml){ $exists=$true; $target=$idxHtml }
      elseif(Test-Path -LiteralPath $idxHtm){ $exists=$true; $target=$idxHtm }
    }

    if(-not $exists){
      $resolved = if($target.StartsWith($root)){ $target.Substring($root.Length+1).Replace('\\','/') } else { $target }
      $broken.Add([pscustomobject]@{Source=$file.FullName.Substring($root.Length+1).Replace('\\','/');Link=$raw;Resolved=$resolved})
      continue
    }

    if(-not (Test-ExactCasePath -fullPath $target)){
      $resolved = if($target.StartsWith($root)){ $target.Substring($root.Length+1).Replace('\\','/') } else { $target }
      $caseIssues.Add([pscustomobject]@{Source=$file.FullName.Substring($root.Length+1).Replace('\\','/');Link=$raw;Resolved=$resolved})
    }
  }
}

Write-Output "HTML files checked: $($files.Count)"
Write-Output "Broken local links: $($broken.Count)"
Write-Output "Case-sensitive path issues: $($caseIssues.Count)"
if($broken.Count -gt 0){
  Write-Output '--- Broken ---'
  $broken | Sort-Object Source,Link | Format-Table -AutoSize | Out-String -Width 500 | Write-Output
}
if($caseIssues.Count -gt 0){
  Write-Output '--- Case Issues ---'
  $caseIssues | Sort-Object Source,Link | Format-Table -AutoSize | Out-String -Width 500 | Write-Output
}
