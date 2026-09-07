<?php
/**
 * POI 플레이그라운드 실행 엔드포인트 (hagora.kr/poi/run.php).
 *
 * POST {"code": "..."}  ->  {"ok", "stdout", "stderr", "exit"}
 *
 * 안전장치:
 *   · POI 안전 모드(--safe): python{}·use py·파일·네트워크·위험 내장 차단
 *   · 별도 프로세스 + 벽시계 타임아웃(강제 종료) + 코드/출력 길이 제한
 *   · 동시 실행 수 제한(파일 락)
 * python 이 없으면 깔끔한 오류 JSON 을 준다 (사이트는 안 죽는다).
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('X-Content-Type-Options: nosniff');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'stdout' => '', 'stderr' => 'POST 로 보내세요.', 'exit' => 1]);
    exit;
}

$raw = file_get_contents('php://input', false, null, 0, 200000);
$req = json_decode($raw, true);
$code = is_array($req) && isset($req['code']) ? (string)$req['code'] : '';
$stdin = is_array($req) && isset($req['stdin']) ? (string)$req['stdin'] : '';

if (strlen($code) === 0) {
    echo json_encode(['ok' => false, 'stdout' => '', 'stderr' => '코드가 비었습니다.', 'exit' => 1]);
    exit;
}
if (strlen($code) > 20000) {
    echo json_encode(['ok' => false, 'stdout' => '', 'stderr' => '코드가 너무 깁니다.', 'exit' => 1]);
    exit;
}

$engine = __DIR__ . DIRECTORY_SEPARATOR . 'engine';  // poi 패키지가 여기 들어있음
$timeout = 6;
$outCap = 64000;

// --- 동시 실행 제한 (간단한 세마포어) ---
$lockDir = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'poi_pg_locks';
@mkdir($lockDir);
$slots = 4;
$held = null;
for ($i = 0; $i < $slots; $i++) {
    $fp = @fopen("$lockDir/slot$i", 'c');
    if ($fp && flock($fp, LOCK_EX | LOCK_NB)) { $held = $fp; break; }
    if ($fp) fclose($fp);
}
if (!$held) {
    echo json_encode(['ok' => false, 'stdout' => '', 'stderr' => '지금 사용량이 많습니다. 잠시 후 다시 시도하세요.', 'exit' => 1]);
    exit;
}

function find_python() {
    $cands = ['python', 'python3', 'py'];
    foreach (['C:\\Python313\\python.exe', 'C:\\Python312\\python.exe',
              'C:\\Python311\\python.exe', 'C:\\xampp\\python\\python.exe',
              '/usr/bin/python3', '/usr/local/bin/python3'] as $p) {
        if (@is_file($p)) return $p;
    }
    foreach ($cands as $c) {
        $which = stripos(PHP_OS, 'WIN') === 0 ? "where $c" : "command -v $c";
        $out = @shell_exec($which . ' 2>&1');
        if ($out && preg_match('/^\s*(\S.+\S)\s*$/m', $out, $m) && @is_file(trim(strtok($out, "\r\n")))) {
            return trim(strtok($out, "\r\n"));
        }
    }
    return null;
}

$py = find_python();
if (!$py) {
    flock($held, LOCK_UN); fclose($held);
    echo json_encode(['ok' => false, 'stdout' => '',
        'stderr' => "이 서버에 python 이 없어 브라우저 실행은 아직 안 됩니다.\n내 컴퓨터에서:  poi run 파일.poi", 'exit' => 1]);
    exit;
}

$tmp = tempnam(sys_get_temp_dir(), 'poi_') . '.poi';
file_put_contents($tmp, $code);

$args = [$py, '-X', 'utf8', '-m', 'poi', 'run', '--safe', '--no-banner',
         '--time', (string)($timeout - 1), $tmp];
$cmd = '';
foreach ($args as $a) { $cmd .= escapeshellarg($a) . ' '; }

$env = ['PYTHONPATH' => $engine, 'POI_NO_UPDATE_CHECK' => '1',
        'POI_NO_BANNER' => '1', 'PYTHONIOENCODING' => 'utf-8'];
$desc = [0 => ['pipe', 'r'], 1 => ['pipe', 'w'], 2 => ['pipe', 'w']];

$proc = proc_open($cmd, $desc, $pipes, sys_get_temp_dir(), $env);
$stdout = ''; $stderr = ''; $exit = 1;
if (is_resource($proc)) {
    fwrite($pipes[0], $stdin);
    fclose($pipes[0]);
    stream_set_blocking($pipes[1], false);
    stream_set_blocking($pipes[2], false);
    $start = microtime(true);
    while (true) {
        $st = proc_get_status($proc);
        $stdout .= (string)stream_get_contents($pipes[1]);
        $stderr .= (string)stream_get_contents($pipes[2]);
        if (!$st['running']) { $exit = $st['exitcode']; break; }
        if (microtime(true) - $start > $timeout) {
            proc_terminate($proc, 9);
            $stderr .= "\n시간이 초과됐습니다 ({$timeout}초).";
            $exit = 1;
            break;
        }
        if (strlen($stdout) > $outCap || strlen($stderr) > $outCap) {
            proc_terminate($proc, 9);
            $stderr .= "\n출력이 너무 많습니다.";
            $exit = 1;
            break;
        }
        usleep(20000);
    }
    fclose($pipes[1]); fclose($pipes[2]);
    proc_close($proc);
}
@unlink($tmp);
flock($held, LOCK_UN); fclose($held);

$stdout = str_replace("\r\n", "\n", $stdout);
$stderr = str_replace("\r\n", "\n", $stderr);
echo json_encode([
    'ok' => $exit === 0,
    'stdout' => mb_substr($stdout, 0, $outCap, 'UTF-8'),
    'stderr' => mb_substr($stderr, 0, $outCap, 'UTF-8'),
    'exit' => $exit,
], JSON_UNESCAPED_UNICODE);
