<?php
session_start();

// Mock database of authorized student records for digital learning portal
$valid_students = [
    "Apex High School" => [
        "STU-2024-001" => "alice.johnson@student.apex.edu",
        "STU-2024-005" => "eva.martinez@student.apex.edu"
    ],
    "Stanford Online Learning" => [
        "STU-2024-008" => "henry.anderson@student.apex.edu"
    ]
];

$message = "";
$message_type = "";

// Check submission
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $submitted_csrf = $_POST['_csrf_token'] ?? '';
    $school = $_POST['school'] ?? '';
    $student_id = $_POST['student_id'] ?? '';
    $email = $_POST['email'] ?? '';

    // Verify CSRF token
    if (empty($submitted_csrf) || !isset($_SESSION['_csrf_token']) || $submitted_csrf !== $_SESSION['_csrf_token']) {
        $message = "Verification failed: CSRF token mismatch or expired. Please refresh the page.";
        $message_type = "error";
    } else {
        // Validate matching ID to email
        if (isset($valid_students[$school][$student_id]) && strtolower($valid_students[$school][$student_id]) === strtolower($email)) {
            $message = "SUCCESS: Sign-up successful! Account created for student " . htmlspecialchars($student_id) . ".";
            $message_type = "success";
        } else {
            $message = "Error: Student record not found or ID and email do not match.";
            $message_type = "error";
        }
    }
}

// Generate fresh CSRF token on EVERY page load / trial
$_SESSION['_csrf_token'] = bin2hex(random_bytes(24));
$csrf_token = $_SESSION['_csrf_token'];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Digital Learning Portal - Sign Up</title>
    <style>
        body { font-family: Arial, sans-serif; background: #1a202c; color: #e2e8f0; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .box { background: #2d3748; padding: 30px; border-radius: 8px; width: 400px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        h2 { text-align: center; color: #63b3ed; margin-top: 0; }
        .msg { padding: 10px; border-radius: 4px; margin-bottom: 15px; font-size: 14px; }
        .msg.success { background: #22543d; color: #9ae6b4; }
        .msg.error { background: #742a2a; color: #feb2b2; }
        label { display: block; margin-top: 10px; font-size: 13px; color: #cbd5e0; }
        input, select { width: 100%; padding: 8px; margin-top: 5px; box-sizing: border-box; border-radius: 4px; border: 1px solid #4a5568; background: #1a202c; color: white; }
        button { width: 100%; margin-top: 20px; padding: 10px; background: #3182ce; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; }
        button:hover { background: #2b6cb0; }
        .token-info { font-size: 11px; color: #a0aec0; margin-top: 15px; word-break: break-all; }
    </style>
</head>
<body>
    <div class="box">
        <h2>Digital Learning Sign-Up</h2>
        <?php if (!empty($message)): ?>
            <div class="msg <?= $message_type ?>"><?= htmlspecialchars($message) ?></div>
        <?php endif; ?>

        <form action="" method="POST">
            <input type="hidden" name="_csrf_token" value="<?= htmlspecialchars($csrf_token) ?>">

            <label for="school">School:</label>
            <select name="school" id="school">
                <option value="Apex High School">Apex High School</option>
                <option value="Stanford Online Learning">Stanford Online Learning</option>
                <option value="Springfield Academy">Springfield Academy</option>
            </select>

            <label for="student_id">Student ID:</label>
            <input type="text" name="student_id" id="student_id" required>

            <label for="email">Student Email:</label>
            <input type="email" name="email" id="email" required>

            <button type="submit">Register Account</button>
        </form>
        <div class="token-info">CSRF Token: <?= htmlspecialchars($csrf_token) ?></div>
    </div>
</body>
</html>
