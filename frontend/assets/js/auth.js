/**
 * FLASHNOVA - Authentication Manager
 * Handles Student & Teacher registration, multi-step subject selection & verification
 */

document.addEventListener("DOMContentLoaded", () => {
  // Bind Student Forms
  const studentRegForm = document.getElementById("form-student-register");
  if (studentRegForm) {
    studentRegForm.addEventListener("submit", handleStudentRegister);
  }

  const studentLoginForm = document.getElementById("form-student-login");
  if (studentLoginForm) {
    studentLoginForm.addEventListener("submit", handleStudentLogin);
  }

  // Bind Teacher Forms
  const teacherRegForm = document.getElementById("form-teacher-register");
  if (teacherRegForm) {
    teacherRegForm.addEventListener("submit", handleTeacherRegister);
  }

  const teacherLoginForm = document.getElementById("form-teacher-login");
  if (teacherLoginForm) {
    teacherLoginForm.addEventListener("submit", handleTeacherLogin);
  }

  const subjectVerifyForm = document.getElementById("form-verify-subject");
  if (subjectVerifyForm) {
    subjectVerifyForm.addEventListener("submit", handleSubjectVerification);
  }

  // Bind Logout
  document.querySelectorAll(".btn-logout").forEach(btn => {
    btn.addEventListener("click", handleLogout);
  });
});

// Student Registration
async function handleStudentRegister(e) {
  e.preventDefault();
  const name = document.getElementById("reg-student-name").value.trim();
  const enrollmentNo = document.getElementById("reg-student-enrollment").value.trim();
  const password = document.getElementById("reg-student-password").value;
  const confirmPassword = document.getElementById("reg-student-confirm").value;
  const isDemo = document.getElementById("reg-student-demo") ? document.getElementById("reg-student-demo").checked : false;

  // Strict 10-digit validation
  if (!/^\d{10}$/.test(enrollmentNo)) {
    showToast("Enrollment number must be exactly 10 numeric digits with no letters, spaces or symbols.", "error");
    return;
  }

  if (password.length < 6) {
    showToast("Password must be at least 6 characters.", "error");
    return;
  }

  if (password !== confirmPassword) {
    showToast("Passwords do not match.", "error");
    return;
  }

  const res = await apiRequest("/api/auth/student/register", {
    method: "POST",
    body: JSON.stringify({
      name: name,
      enrollment_no: enrollmentNo,
      password: password,
      confirm_password: confirmPassword,
      is_demo: isDemo
    })
  });

  if (res.success) {
    showToast("Registration successful! Welcome to FLASHNOVA.", "success");
    if (res.token) localStorage.setItem("flashnova_token", res.token);
    localStorage.setItem("flashnova_user", JSON.stringify(res.user));
    setTimeout(() => {
      window.location.href = "student.html";
    }, 1000);
  } else {
    showToast(res.error || "Registration failed.", "error");
  }
}

// Student Login
async function handleStudentLogin(e) {
  e.preventDefault();
  const enrollmentNo = document.getElementById("login-student-enrollment").value.trim();
  const password = document.getElementById("login-student-password").value;

  if (!enrollmentNo || !password) {
    showToast("Please enter your 10-digit enrollment number and password.", "error");
    return;
  }

  const res = await apiRequest("/api/auth/student/login", {
    method: "POST",
    body: JSON.stringify({
      enrollment_no: enrollmentNo,
      password: password
    })
  });

  if (res.success) {
    showToast("Login successful. Launching student portal...", "success");
    if (res.token) localStorage.setItem("flashnova_token", res.token);
    localStorage.setItem("flashnova_user", JSON.stringify(res.user));
    setTimeout(() => {
      window.location.href = "student.html";
    }, 800);
  } else {
    showToast(res.error || "Invalid credentials.", "error");
  }
}

// Teacher Registration
async function handleTeacherRegister(e) {
  e.preventDefault();
  const name = document.getElementById("reg-teacher-name").value.trim();
  const username = document.getElementById("reg-teacher-username").value.trim();
  const department = document.getElementById("reg-teacher-dept").value.trim();
  const password = document.getElementById("reg-teacher-password").value;
  const confirmPassword = document.getElementById("reg-teacher-confirm").value;

  if (password !== confirmPassword) {
    showToast("Passwords do not match.", "error");
    return;
  }

  const res = await apiRequest("/api/auth/teacher/register", {
    method: "POST",
    body: JSON.stringify({
      name: name,
      username: username,
      department: department,
      password: password,
      confirm_password: confirmPassword
    })
  });

  if (res.success) {
    showToast("Teacher account created! Now login to select your subject.", "success");
    closeModal("modal-teacher-register");
    openModal("modal-teacher-login");
  } else {
    showToast(res.error || "Registration failed.", "error");
  }
}

// Teacher Login (Step 1)
async function handleTeacherLogin(e) {
  e.preventDefault();
  const username = document.getElementById("login-teacher-username").value.trim();
  const password = document.getElementById("login-teacher-password").value;

  const res = await apiRequest("/api/auth/teacher/login", {
    method: "POST",
    body: JSON.stringify({
      username: username,
      password: password
    })
  });

  if (res.success) {
    if (res.token) localStorage.setItem("flashnova_token", res.token);
    localStorage.setItem("flashnova_user", JSON.stringify(res.user));
    closeModal("modal-teacher-login");
    // Advance to Step 2: Subject Selection
    openSubjectSelectionModal();
  } else {
    showToast(res.error || "Teacher login failed.", "error");
  }
}

// Open Step 2: Subject Selection Modal
let selectedSubjectCode = null;
function openSubjectSelectionModal() {
  openModal("modal-teacher-subjects");
  document.querySelectorAll(".subject-select-card").forEach(card => {
    card.onclick = () => {
      document.querySelectorAll(".subject-select-card").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
      selectedSubjectCode = card.getAttribute("data-subject-code");
      
      // Advance to Step 3: Verify Access Code
      document.getElementById("verify-subject-title").innerText = `Verify Access Code for ${card.getAttribute("data-subject-name")} (${selectedSubjectCode})`;
      closeModal("modal-teacher-subjects");
      openModal("modal-verify-subject");
    };
  });
}

// Step 3: Subject Access Code Verification
async function handleSubjectVerification(e) {
  e.preventDefault();
  const accessCode = document.getElementById("input-access-code").value.trim();

  if (!selectedSubjectCode || !accessCode) {
    showToast("Please enter the access code.", "error");
    return;
  }

  const res = await apiRequest("/api/auth/teacher/verify-subject", {
    method: "POST",
    body: JSON.stringify({
      subject_code: selectedSubjectCode,
      access_code: accessCode
    })
  });

  if (res.success) {
    showToast(`Subject verified! Entering classroom control center...`, "success");
    localStorage.setItem("flashnova_subject", JSON.stringify(res.subject));
    setTimeout(() => {
      window.location.href = "teacher.html";
    }, 1000);
  } else {
    showToast(res.error || "Incorrect access code. Access rejected.", "error");
  }
}

// Logout
async function handleLogout() {
  await apiRequest("/api/auth/logout", { method: "POST" });
  localStorage.removeItem("flashnova_token");
  localStorage.removeItem("flashnova_user");
  localStorage.removeItem("flashnova_subject");
  showToast("Logged out successfully.", "info");
  setTimeout(() => {
    window.location.href = "index.html";
  }, 500);
}
