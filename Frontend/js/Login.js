
const $submit = document.getElementById("submit"),
  $password = document.getElementById("password"),
  $email = document.getElementById("email"),
  $visible = document.getElementById("visible");

document.addEventListener("change", (e)=>{
  if(e.target === $visible){
    if($visible.checked === false) $password.type = "password";
    else $password.type = "text";
  }
})

document.addEventListener("click", (e)=>{
  if(e.target === $submit){
    if($password.value !== "" && $email.value !== ""){
      e.preventDefault();
      window.location.href = "dashboard.html";
    }
  }
})

