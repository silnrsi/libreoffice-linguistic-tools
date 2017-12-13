program TestOO;

{$IFDEF FPC}
 {$MODE Delphi}
{$ELSE}
 {$APPTYPE CONSOLE}
{$ENDIF} 

uses
  SysUtils, Variants, ComObj;
var
    ServiceManager: Variant;
    Desktop: Variant;
    Controller: Variant;
    NoParams : Variant;
    Document : Variant;
    TextCursor : Variant;
    ViewCursor : Variant;
    SearchDescriptor : Variant;
    Found : Variant;
    IdNumber : String;
    Txt : Variant;
    Graphic : Variant;
    ImageURL : String;
    Bitmaps : Variant;
    InternalName : String;
    EmbeddedName : String;
begin
    WriteLn('Beginning...');
    ServiceManager := CreateOleObject('com.sun.star.ServiceManager');
    Desktop := ServiceManager.CreateInstance('com.sun.star.frame.Desktop');
    {Document := Desktop.getCurrentComponent();}
    NoParams := VarArrayCreate([0, -1], varVariant);
    Document := Desktop.LoadComponentFromURL('private:factory/swriter', '_blank', 0, NoParams);
    Controller := Document.getCurrentController;
    ViewCursor := Controller.getViewCursor;
    WriteLn('10');
    Txt := Document.getText;
    TextCursor := Txt.createTextCursor;
    Txt.insertString(TextCursor, 'SHOW_CHART=123' + #10, False);
    Txt.insertString(TextCursor, 'SHOW_CHART=456' + #10, False);
    WriteLn('20');
    Bitmaps := Document.createInstance('com.sun.star.drawing.BitmapTable');
    SearchDescriptor := Document.createSearchDescriptor;
    SearchDescriptor.setSearchString('SHOW_CHART=[0-9]+');
    SearchDescriptor.SearchRegularExpression := True;
    WriteLn('30');
    Found := Document.findFirst(SearchDescriptor);
    WriteLn('40');
    While Not (VarIsNull(Found) or VarIsEmpty(Found) or VarIsType(Found,varUnknown)) do
    begin
        WriteLn('50');
        {S := Found.getString;
        IdNumber := copy(S, Length('SHOW_CHART='));}
        {IdNumber := copy(Found.getString, Length('SHOW_CHART='));}
        IdNumber := copy(String(Found.getString), Length('SHOW_CHART=') + 1);
        {IdNumber := '123';}
        WriteLn('Got "' + IdNumber + '"');
        Found.setString('');
        Graphic := Document.createInstance('com.sun.star.text.GraphicObject');
        WriteLn('60');
        {Graphic.GraphicURL := String('file:///C:/OurDocs/test_img' + IdNumber + '.jpg');}
        {Graphic.GraphicURL := 'file:///C:/OurDocs/test_img123.jpg';}
        {Graphic.GraphicURL := String('file:///C:/OurDocs/test_img123.jpg');}
        {Graphic.GraphicURL := String('file:///C:/OurDocs/test_img' + '123' + '.jpg');}
        {ImageURL := 'file:///C:/OurDocs/test_img' + IdNumber + '.jpg';}
        {ImageURL := 'file:///C:/OurDocs/test_img123.jpg';}
        {WriteLn('ImageURL = "' + ImageURL + '"');}
        {Graphic.GraphicURL := String('file:///C:/OurDocs/test_img' + IdNumber + '.jpg');}
        {Graphic.GraphicURL := ImageURL;}
        {WriteLn('file:///C:/OurDocs/test_img' + IdNumber + '.jpg');}
        If IdNumber = '123' Then begin
            Bitmaps.insertByName('123Jpg', 'file:///C:/OurDocs/test_img123.jpg');
            Graphic.GraphicURL := Bitmaps.getByName('123Jpg');
        end Else begin
            Bitmaps.insertByName('456Jpg', 'file:///C:/OurDocs/test_img456.jpg');
            Graphic.GraphicURL := Bitmaps.getByName('456Jpg');
        end;
        WriteLn('GraphicURL = "' + Graphic.GraphicURL + '"');
        Graphic.AnchorType := 1; {com.sun.star.text.TextContentAnchorType.AS_CHARACTER;}
        Graphic.Width := 6000;
        Graphic.Height := 8000;
        WriteLn('70');
        TextCursor.gotoRange(Found, False);
        Txt.insertTextContent(TextCursor, Graphic, False);
        WriteLn('80');
        Found := Document.findNext(Found.getEnd, SearchDescriptor);
        WriteLn('90');
    end;
    WriteLn('Done!');
    {TextCursor.setString('Hello, World!');}
    {ViewCursor.setString('Hi');}
{
  StarDocument.Close(True);
  Desktop.Terminate;
  ServiceManager := Unassigned;
}
end.
