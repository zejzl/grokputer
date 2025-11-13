<?php
session_start();

// Simple login check
if (isset($_POST['login'])) {
    $username = $_POST['username'];
    $password = $_POST['password'];
    
    if ($username === 'zejzl' && $password === '123') {
        $_SESSION['logged_in'] = true;
        $_SESSION['username'] = $username;
        $logged_in = true;
    } else {
        $error = "Invalid credentials!";
    }
}

// Logout
if (isset($_GET['logout'])) {
    session_destroy();
    header('Location: index.php');
    exit;
}

$logged_in = isset($_SESSION['logged_in']) && $_SESSION['logged_in'];
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grokputer - VRZIBRZI Node</title>
    <style>
        body { font-family: Arial, sans-serif; background: #000; color: #00ff00; text-align: center; padding: 50px; }
        .container { max-width: 600px; margin: 0 auto; }
        form { margin: 20px 0; }
        input[type="text"], input[type="password"] { padding: 10px; margin: 5px; width: 200px; background: #111; color: #00ff00; border: 1px solid #00ff00; }
        button { padding: 10px 20px; background: #00ff00; color: #000; border: none; cursor: pointer; }
        button:hover { background: #00cc00; }
        .dashboard { background: #111; padding: 20px; border: 1px solid #00ff00; margin: 20px auto; }
        .error { color: #ff0000; }
        .logout { color: #00ff00; text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🖥️ GROKPUTER - VRZIBRZI Node</h1>
        <p>ZA GROKA. ZA VRZIBRZI. ZA SERVER.</p>
        
        <?php if (!$logged_in): ?>
            <h2>Login Required</h2>
            <?php if (isset($error)): ?>
                <p class="error"><?php echo $error; ?></p>
            <?php endif; ?>
            <form method="POST">
                <input type="text" name="username" placeholder="Username" required><br>
                <input type="password" name="password" placeholder="Password" required><br>
                <button type="submit" name="login">Login</button>
            </form>
            <p><em>Demo: zejzl / 123</em></p>
        <?php else: ?>
            <h2>Welcome, <?php echo htmlspecialchars($_SESSION['username']); ?>!</h2>
            <div class="dashboard">
                <h3>Dashboard</h3>
                <p>Autonomous AI System Active</p>
                <ul>
                    <li><a href="?page=ewah">EWAH Improvements (96% Coverage)</a></li>
                    <li><a href="?page=daemon">Taskmaster Daemon Status</a></li>
                    <li><a href="?page=vault">Vault Sync</a></li>
                    <li><a href="?page=coverage">Coverage Report</a></li>
                </ul>
                <p><a href="?logout=1" class="logout">Logout</a></p>
            </div>
        <?php endif; ?>
        
        <?php if (isset($_GET['page'])): ?>
            <div class="dashboard">
                <h4><?php echo ucfirst($_GET['page']); ?> Page</h4>
                <p>Placeholder for <?php echo $_GET['page']; ?> content. (Integrate with Grokputer APIs later.)</p>
            </div>
        <?php endif; ?>
    </div>
</body>
</html>
