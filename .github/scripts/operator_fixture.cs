using System;
using System.Drawing;
using System.Windows.Forms;
class OperatorFixture {
 [STAThread] static void Main() {
  Application.EnableVisualStyles();
  var form=new Form {Text="Cypher Operator Fixture",Width=600,Height=400,TopMost=true};
  var edit=new TextBox {AccessibleName="Document text",Multiline=true,Left=20,Top=20,Width=500,Height=140};
  var secret=new TextBox {AccessibleName="Secret field",UseSystemPasswordChar=true,Text="fixture-secret",Left=20,Top=180};
  var button=new Button {Text="Apply document",AccessibleName="Apply document",Left=20,Top=220,Width=180};
  var label=new Label {Text="Waiting",Left=20,Top=270,Width=400};
  button.Click += (s,e) => { label.Text="Applied"; };
  form.Controls.Add(edit);form.Controls.Add(secret);form.Controls.Add(button);form.Controls.Add(label);
  Application.Run(form);
 }
}
