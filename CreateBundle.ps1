$output = @()
foreach ($file in Get-ChildItem "$PSScriptRoot\resources\snes"  -Recurse -Filter tracks.json)
{
    $data = Get-Content -Raw -Path $file.fullname | ConvertFrom-Json
    $output += $data
}
$output | ConvertTo-Json -Depth 10 | Out-File -FilePath "$PSScriptRoot\msu_types.json"
$output = git describe --tags --abbrev=0 | Out-String
$output = [int]($output -replace "[^0-9\.]", "")
$output = $output + 1
Write-Output "tag=v$output.0" >> $env:GITHUB_OUTPUT