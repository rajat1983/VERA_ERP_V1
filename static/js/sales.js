function addRow(){
  let row = document.querySelector("#items tbody tr").cloneNode(true);
  document.querySelector("#items tbody").appendChild(row);
}
function removeRow(btn){
  btn.closest("tr").remove();
}