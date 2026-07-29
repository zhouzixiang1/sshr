param(
    [string]$MainTex = "submission_competition/main.tex",
    [string]$BibFile = "submission_competition/references.bib",
    [string]$OutputPrefix = "submission_competition/literature_verification_audit"
)

$ErrorActionPreference = "Stop"

function Normalize-Title([string]$Value) {
    if ($null -eq $Value) { return "" }
    $text = $Value.ToLowerInvariant()
    $text = $text -replace '\\[a-zA-Z]+', ' '
    $text = $text -replace '[{}$\\]', ''
    $text = $text -replace '[^\p{L}\p{Nd}]+', ' '
    return ($text -replace '\s+', ' ').Trim()
}

function Normalize-Name([string]$Value) {
    if ($null -eq $Value) { return "" }
    # Collapse common one-letter LaTeX accents (e.g. F{\"u}rrutter) before
    # applying Unicode diacritic removal to the registry spelling.
    $text = $Value -replace '\{\\[^A-Za-z]?([A-Za-z])\}', '$1'
    $text = $text -replace '[^\p{L}\p{Nd}]', ''
    $decomposed = $text.Normalize([Text.NormalizationForm]::FormD)
    $builder = [Text.StringBuilder]::new()
    foreach ($character in $decomposed.ToCharArray()) {
        if ([Globalization.CharUnicodeInfo]::GetUnicodeCategory($character) -ne [Globalization.UnicodeCategory]::NonSpacingMark) {
            [void]$builder.Append($character)
        }
    }
    return (Normalize-Title $builder.ToString())
}

function Token-Jaccard([string]$Left, [string]$Right) {
    $stop = @('a','an','the','in','of','for','on','to','and','with','by')
    $a = @(Normalize-Title $Left -split ' ' | Where-Object { $_ -and $_ -notin $stop } | Sort-Object -Unique)
    $b = @(Normalize-Title $Right -split ' ' | Where-Object { $_ -and $_ -notin $stop } | Sort-Object -Unique)
    $union = @($a + $b | Sort-Object -Unique)
    if ($union.Count -eq 0) { return 0.0 }
    $intersection = @($a | Where-Object { $_ -in $b })
    return [double]$intersection.Count / [double]$union.Count
}

function Parse-Bib([string]$Path) {
    $text = Get-Content -Raw -LiteralPath $Path
    $matches = [regex]::Matches(
        $text,
        '(?ms)^@(?<type>\w+)\{(?<key>[^,]+),(?<body>.*?)(?=^@\w+\{|\z)'
    )
    $entries = @()
    foreach ($match in $matches) {
        $fields = @{}
        foreach ($line in ($match.Groups['body'].Value -split "`r?`n")) {
            if ($line -match '^\s*(?<name>[A-Za-z]+)\s*=\s*\{(?<value>.*)\}\s*,?\s*$') {
                $fields[$Matches['name'].ToLowerInvariant()] = $Matches['value']
            }
        }
        $entries += [pscustomobject]@{
            entry_type = $match.Groups['type'].Value.ToLowerInvariant()
            key = $match.Groups['key'].Value.Trim()
            fields = $fields
        }
    }
    return $entries
}

function Evidence-Role([string]$Key) {
    $roles = @{
        gupta2006pprm = @('PPRM/Reed--Muller factoring', 'Does not establish mapped native-gate superiority')
        fazel2007esop = @('ESOP-to-Toffoli cascade baseline', 'Does not establish fault-tolerant T cost after decomposition')
        wille2009bdd = @('BDD scalability route', 'Does not imply low mapped depth on the present target')
        meuli2019multiplicative = @('Multiplicative-complexity/T-count oracle bound', 'Uses a different logic-network and ancilla contract')
        meuli2020ros = @('Resource-constrained LUT oracle synthesis', 'Not reproduced here as the official ROS SAT implementation')
        meuli2022xag = @('XAG qubit/T-count/T-depth trade-off', 'Not a same-implementation mapping baseline in primary20')
        henderson2023minimal = @('Oracle qubit/domain-preservation trade-off', 'Different embedding contract; no direct optimality transfer')
        yu2025backend = @('Back-end-aware fault-tolerant oracle synthesis', 'Different backend cost model; no direct win claim')
        zheng2025sshr = @('Closest small-Boolean CNOT-oriented baseline', 'Only locally reimplemented SSHR-H/Beam variants are compared')
        wang2023nestedmcts = @('MCTS for automated circuit design', 'Different parameterized-circuit task')
        weiden2023qseed = @('Learning-seeded unitary synthesis', 'Does not prove learned-prior gain in Boolean-oracle search')
        rietsch2024rlsynthesis = @('RL Clifford+T unitary synthesis', 'Different action space and objective')
        tsaras2024shortcircuit = @('AlphaZero-driven classical circuit design', 'Classical circuit task, not mapped quantum-oracle evidence')
        fuerrutter2024diffusion = @('Diffusion-based circuit generation/editing', 'Not a bit-flip Boolean-oracle baseline')
        ruiz2025alphatensor = @('AlphaTensor T-count optimization', 'Starts from existing CNOT+T circuits; different causal target')
        riu2025rlzx = @('RL-guided ZX rewrite selection', 'Different representation and equivalence mechanism')
        zen2025rlft = @('Hardware-constrained RL circuit discovery', 'Fault-tolerant state preparation, not a Boolean-oracle baseline')
        li2019sabre = @('SABRE layout/routing method', 'Does not provide hardware calibration evidence by itself')
        cowtan2019routing = @('Formal qubit-routing problem framing', 'Routing theory is not oracle-synthesis quality evidence')
        nannicini2022ilp = @('Optimal assignment/routing counterpoint', 'Not run in primary20 and no optimality claim is transferred')
        murali2019noiseadaptive = @('Calibration-aware mapping', 'Present study uses uncalibrated synthetic targets')
        hartnett2024learningtorank = @('Hardware-data circuit ranking', 'Present learned scorer is not trained on hardware data')
        li2025hopps = @('Hardware-aware CNOT+Rz phase-polynomial synthesis', 'No Rz backend here; preprint is boundary evidence only')
    }
    if ($roles.ContainsKey($Key)) { return $roles[$Key] }
    return @('Unclassified supporting reference', 'Manual scope check required')
}

$tex = Get-Content -Raw -LiteralPath $MainTex
$citeKeys = @()
foreach ($match in [regex]::Matches($tex, '\\cite[a-zA-Z]*\{([^}]+)\}')) {
    $citeKeys += $match.Groups[1].Value -split ',' | ForEach-Object { $_.Trim() }
}
$citeKeys = @($citeKeys | Where-Object { $_ } | Sort-Object -Unique)
$entries = @(Parse-Bib $BibFile)
$entryByKey = @{}
foreach ($entry in $entries) { $entryByKey[$entry.key] = $entry }

$headers = @{
    'User-Agent' = 'Resource-NMCTS-literature-audit/1.0 (competition artifact; Crossref metadata verification)'
}
$rows = @()
foreach ($key in $citeKeys) {
    if (-not $entryByKey.ContainsKey($key)) {
        $rows += [pscustomobject]@{
            key = $key; status = 'not_found'; doi = ''; arxiv = '';
            title_bib = ''; title_source = ''; title_similarity = 0.0;
            year_bib = ''; year_source = ''; first_author_bib = '';
            first_author_source = ''; venue_bib = ''; venue_source = '';
            source_tier = 'none'; source_url = ''; evidence_role = '';
            prohibited_inference = 'Citation key is absent from references.bib'; notes = 'missing BibTeX entry'
        }
        continue
    }
    $entry = $entryByKey[$key]
    $f = $entry.fields
    $doi = if ($f.ContainsKey('doi')) { $f['doi'] } else { '' }
    $arxiv = if ($f.ContainsKey('eprint')) { $f['eprint'] } else { '' }
    $titleBib = if ($f.ContainsKey('title')) { $f['title'] } else { '' }
    $yearBib = if ($f.ContainsKey('year')) { $f['year'] } else { '' }
    $venueBib = if ($f.ContainsKey('journal')) { $f['journal'] } elseif ($f.ContainsKey('booktitle')) { $f['booktitle'] } else { '' }
    $authorBib = if ($f.ContainsKey('author')) { (($f['author'] -split '\s+and\s+')[0] -split ',')[0].Trim() } else { '' }
    $titleSource = ''
    $yearSource = ''
    $venueSource = ''
    $authorSource = ''
    $sourceUrl = ''
    $sourceTier = 'T1'
    $notes = @()
    $resolved = $false

    if ($doi -and -not $doi.StartsWith('10.48550/', [System.StringComparison]::OrdinalIgnoreCase)) {
        $escapedDoi = [uri]::EscapeDataString($doi)
        try {
            $response = Invoke-RestMethod -Uri "https://api.crossref.org/works/$escapedDoi" -Headers $headers -TimeoutSec 30
            $message = $response.message
            $titleSource = [string]$message.title[0]
            $venueSource = [string]$message.'container-title'[0]
            if ($message.author.Count -gt 0) { $authorSource = [string]$message.author[0].family }
            $date = if ($message.'published-print') { $message.'published-print' } elseif ($message.published) { $message.published } else { $message.issued }
            if ($date.'date-parts'[0].Count -gt 0) { $yearSource = [string]$date.'date-parts'[0][0] }
            $sourceUrl = "https://doi.org/$doi"
            $resolved = $true
        }
        catch {
            $notes += "Crossref lookup failed: $($_.Exception.Message)"
        }
    }

    if (-not $resolved -and $arxiv) {
        try {
            $feed = Invoke-RestMethod -Uri "https://export.arxiv.org/api/query?id_list=$arxiv" -Headers $headers -TimeoutSec 30
            $atomEntry = if ($feed.LocalName -eq 'entry') { $feed } else { $feed.feed.entry }
            if ($atomEntry) {
                $titleSource = ([string]$atomEntry.title -replace '\s+', ' ').Trim()
                $authorSource = [string]$atomEntry.author[0].name
                if ($authorSource -match '^(?<given>.+)\s+(?<family>\S+)$') { $authorSource = $Matches['family'] }
                $yearSource = ([datetime]$atomEntry.published).Year.ToString()
                $venueSource = 'arXiv'
                $sourceUrl = "https://arxiv.org/abs/$arxiv"
                $resolved = $true
            }
        }
        catch {
            $notes += "arXiv lookup failed: $($_.Exception.Message)"
        }
    }

    $titleScore = if ($resolved) { Token-Jaccard $titleBib $titleSource } else { 0.0 }
    $yearMatch = $resolved -and $yearBib -eq $yearSource
    $authorMatch = $resolved -and (Normalize-Name $authorBib) -eq (Normalize-Name $authorSource)
    $venueScore = if ($venueSource -eq 'arXiv') { 1.0 } elseif ($resolved -and $venueBib -and $venueSource) { Token-Jaccard $venueBib $venueSource } else { 1.0 }
    $status = if (-not $resolved) {
        'manual_needed'
    } elseif ($titleScore -ge 0.85 -and $yearMatch -and $authorMatch -and $venueScore -ge 0.45) {
        'verified'
    } elseif ($titleScore -ge 0.75 -and $yearMatch -and $authorMatch) {
        'suspicious'
    } else {
        'mismatch'
    }
    if ($resolved -and $venueSource -ne 'arXiv' -and $venueBib -and $venueScore -lt 0.45) { $notes += "container-title differs in wording" }
    $role = Evidence-Role $key
    $rows += [pscustomobject]@{
        key = $key
        status = $status
        doi = $doi
        arxiv = $arxiv
        title_bib = $titleBib
        title_source = $titleSource
        title_similarity = [math]::Round($titleScore, 4)
        year_bib = $yearBib
        year_source = $yearSource
        first_author_bib = $authorBib
        first_author_source = $authorSource
        venue_bib = $venueBib
        venue_source = $venueSource
        source_tier = $sourceTier
        source_url = $sourceUrl
        evidence_role = $role[0]
        prohibited_inference = $role[1]
        notes = ($notes -join '; ')
    }
    Start-Sleep -Milliseconds 100
}

$counts = @{}
foreach ($status in @('verified','mismatch','not_found','suspicious','manual_needed')) {
    $counts[$status] = @($rows | Where-Object { $_.status -eq $status }).Count
}
$unused = @($entries.key | Where-Object { $_ -notin $citeKeys } | Sort-Object)
$missing = @($citeKeys | Where-Object { $_ -notin $entries.key } | Sort-Object)
$payload = [ordered]@{
    schema_version = 1
    generated_utc = [datetime]::UtcNow.ToString('o')
    workflow = @('citation-verification','multi-source-search-gap-check')
    source_policy = 'T1 Crossref DOI metadata; arXiv Atom fallback; no scraped source used for verification status'
    main_tex = $MainTex.Replace('\','/')
    bibliography = $BibFile.Replace('\','/')
    cited_key_count = $citeKeys.Count
    bib_entry_count = $entries.Count
    counts = $counts
    missing_bib_keys = $missing
    unused_bib_keys = $unused
    coverage_roles = [ordered]@{
        boolean_and_reversible_synthesis = @($rows | Where-Object { $_.key -in @('gupta2006pprm','fazel2007esop','wille2009bdd','meuli2019multiplicative','meuli2020ros','meuli2022xag','henderson2023minimal','yu2025backend','zheng2025sshr') }).Count
        learning_and_search = @($rows | Where-Object { $_.key -in @('wang2023nestedmcts','weiden2023qseed','rietsch2024rlsynthesis','tsaras2024shortcircuit','fuerrutter2024diffusion','ruiz2025alphatensor','riu2025rlzx','zen2025rlft') }).Count
        hardware_mapping_and_routing = @($rows | Where-Object { $_.key -in @('li2019sabre','cowtan2019routing','nannicini2022ilp','murali2019noiseadaptive','hartnett2024learningtorank','li2025hopps') }).Count
    }
    gap_search = @(
        [ordered]@{
            candidate = 'Henderson et al., Automated Quantum Oracle Synthesis with a Minimal Number of Qubits (2023)'
            url = 'https://arxiv.org/abs/2304.03829'
            relevance = 'direct oracle/qubit-domain-preservation trade-off; useful scope context'
            decision = 'added_to_review'
        },
        [ordered]@{
            candidate = 'Li et al., HOPPS: Hardware-Aware Optimal Phase Polynomial Synthesis (2025 preprint)'
            url = 'https://arxiv.org/abs/2511.18770'
            relevance = 'current hardware-aware CNOT+Rz phase-polynomial boundary'
            decision = 'added_as_boundary_only'
        },
        [ordered]@{
            candidate = 'Zen et al., Quantum Circuit Discovery for Fault-Tolerant Logical State Preparation with Reinforcement Learning (2025)'
            url = 'https://arxiv.org/abs/2402.17761'
            relevance = 'hardware-constrained RL circuit discovery, but different fault-tolerant state-preparation task'
            decision = 'added_as_boundary_only'
        }
    )
    records = $rows
}

$jsonPath = "$OutputPrefix.json"
$csvPath = "$OutputPrefix.csv"
$mdPath = "$OutputPrefix.md"
$payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding utf8
$rows | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding utf8

$md = @()
$md += '# 文献核对与证据职责审计'
$md += ''
$md += "- 工作流：citation-verification + multi-source-search gap check"
$md += "- 实际引用：$($citeKeys.Count)；BibTeX 条目：$($entries.Count)"
$md += "- 状态：verified=$($counts.verified)，suspicious=$($counts.suspicious)，mismatch=$($counts.mismatch)，not_found=$($counts.not_found)，manual_needed=$($counts.manual_needed)"
$md += "- 缺失 citation key：$(if($missing.Count){$missing -join ', '}else{'无'})；未使用 BibTeX：$(if($unused.Count){$unused -join ', '}else{'无'})"
$md += '- 核对源：Crossref DOI 元数据；10.48550/arXiv 使用 arXiv Atom fallback。验证状态不依赖抓取式数据库。'
$md += ''
$md += '| key | 状态 | 年份 | 题名相似度 | 证据职责 | 禁止外推 | 来源 |'
$md += '|---|---:|---:|---:|---|---|---|'
foreach ($row in $rows) {
    $safeRole = $row.evidence_role -replace '\|','/'
    $safeBoundary = $row.prohibited_inference -replace '\|','/'
    $link = if ($row.source_url) { "[source]($($row.source_url))" } else { '—' }
    $md += "| $($row.key) | $($row.status) | $($row.year_bib)/$($row.year_source) | $($row.title_similarity) | $safeRole | $safeBoundary | $link |"
}
$md += ''
$md += '## 定向补缺建议'
$md += ''
foreach ($gap in $payload.gap_search) {
    $md += "- [$($gap['candidate'])]($($gap['url']))：$($gap['relevance'])；处理：$($gap['decision'])。"
}
$md += ''
$md += '## 解释边界'
$md += ''
$md += '现有综述已覆盖同任务 Boolean/Oracle 综合、学习/搜索和硬件映射三层。不同任务论文只用于定位方法空间，不得作为 primary20 的数值基线；未经同输入、同辅助位、同超时和同映射配置重跑的论文结果不得进入胜负统计。'
$md -join "`n" | Set-Content -LiteralPath $mdPath -Encoding utf8

[pscustomobject]@{
    cited = $citeKeys.Count
    bib_entries = $entries.Count
    verified = $counts.verified
    suspicious = $counts.suspicious
    mismatch = $counts.mismatch
    not_found = $counts.not_found
    manual_needed = $counts.manual_needed
    json = $jsonPath
    csv = $csvPath
    markdown = $mdPath
} | ConvertTo-Json -Depth 3
