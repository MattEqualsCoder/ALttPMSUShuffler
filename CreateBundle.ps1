$output = @()
foreach ($file in Get-ChildItem "$PSScriptRoot\resources\snes"  -Recurse -Filter tracks.json)
{
    $data = Get-Content -Raw -Path $file.fullname | ConvertFrom-Json
    $output += $data
}
$output | ConvertTo-Json -Depth 10 | Out-File -FilePath "$PSScriptRoot\msu_types.json"
