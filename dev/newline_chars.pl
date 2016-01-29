# Cre 29-Mar-2011 by Jim
# for testing how OOo handles newline chars
# It is helpful to view results in Notepad++ with View -> Show symbol -> EOL.

open(OUTFILE, "> newline_chars.txt").
print OUTFILE "one\ntwo\r\nthree\n\rfour\rfive\n";
close OUTFILE;

