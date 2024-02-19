$output = @()
foreach ($file in Get-ChildItem "$PSScriptRoot\resources\snes"  -Recurse -Filter tracks.json)
{
    $data = Get-Content -Raw -Path $file.fullname | ConvertFrom-Json
    $filename = (Get-Item $file.FullName).Directory.Parent.Name
    Add-Member -InputObject $data.meta -NotePropertyName "path" -NotePropertyValue "snes/$filename"
    $output += $data
}
$output | ConvertTo-Json -Depth 10 | Out-File -FilePath "$PSScriptRoot\msu_types.json"

$prevVersion = 0.0

$tags = git tag
foreach ($tag in $tags)
{
    $culture = Get-Culture
    $version = [decimal]::Parse(($tag -replace "[^0-9\.]", ""))

    if ($version -gt $prevVersion)
    {
        $prevVersion = $version
    }

}

$newVersion = "v$($prevVersion + 1)"
Write-Output "tag=$newVersion" >> $env:GITHUB_OUTPUT
