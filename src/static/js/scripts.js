function addField() {
    const fieldsDiv = document.getElementById("fields");
    const input = document.createElement("input");
    input.type = "text";
    input.name = "fields[]";
    input.placeholder = "Field Name";
    fieldsDiv.appendChild(input);
}
