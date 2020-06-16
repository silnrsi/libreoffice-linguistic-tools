#-------------------------------------------------------------------------------
#
# dialog_strings_read.pl
#
# This code deals with the files in LingToolsBasic.
# Often the localized strings get messed up, and in any case they are sorted by
# most recent changes first rather than just by dialog, so over time it becomes
# hard to follow.
#
# Grab all of the strings and put them in a tab-delimited file suitable for
# managing in a spreadsheet. Also make new IDs sorted only by dialog id and
# control id.
#
# Currently dlg:menuitem is not supported. The recommended workaround is to put
# non-localized menuitem values directly in the dialogs rather than the
# strings list, and populate localized menuitem values by code.
#
# For now, set all help text to "" since we don't use it.
# This could possibly change in a future version of LOLT.
#
# Created by Jim on March 22 2013
#
# 29-Mar-13 JDK  Add support for frame controls (titled boxes).
# 06-Mar-17 JDK  Use paths relative to the build directory.
#
#-------------------------------------------------------------------------------
use strict;
use File::Spec;

my $OUTFOLDER = ".\\";  # the current folder
my $INFOLDER  = '..\\..\\LingToolsBasic';
my $OS = $^O;   # linux or MSWin32
print "Running in $OS\n";
if ($OS eq 'linux') {
    $OUTFOLDER =~ s!\\!/!g;
    $INFOLDER  =~ s!\\!/!g;
}
my $OUTFILE = File::Spec->catfile($OUTFOLDER, "dialog_strings.csv");

my $TRUE   = 1;
my $FALSE  = 0;
my $EXISTS = 'e';

my %Strings;   # keys are dialogID.controlID
               # values are [stringID, stringEN, stringES, stringFR]
my %Titles;    # same but keys are just dialogID
my ($I_STRING_ID, $I_EN, $I_ES, $I_FR) = (0,1,2,3);

#-------------------------------------------------------------------------------
# Read files in the LingToolsBasic folder.
#-------------------------------------------------------------------------------

my @DialogFiles;
my @StringsFiles;
opendir(INFOLDER, $INFOLDER) || die "Couldn't open $INFOLDER for reading.";
readdir INFOLDER;   # .
readdir INFOLDER;   # ..
while (my $filename = readdir INFOLDER)
{
    if ($filename =~ /\.xdl$/)
    {
        push @DialogFiles, File::Spec->catfile($INFOLDER, $filename);
    }
    elsif ($filename =~ /\.properties$/)
    {
        push @StringsFiles, File::Spec->catfile($INFOLDER, $filename);
    }
}
foreach my $filepath (@DialogFiles)
{
    &read_dialog_file($filepath);
}
foreach my $filepath (@StringsFiles)
{
    &read_strings_file($filepath);
}
    

#-------------------------------------------------------------------------------
#
# sub read_dialog_file
#
#-------------------------------------------------------------------------------
sub read_dialog_file
{
    my ($infile) = @_;

    my $dlgID;
    my $titledBoxID;
    open (INFILE, "< $infile") || die "Couldn't open $infile";
    while (my $line = scalar(<INFILE>))
    {
        if ($line =~ /dlg:window.+dlg:id="(\w+)".+dlg:title="([^"]+)"/)
        {
            my $stringID;
            ($dlgID, $stringID) = ($1, $2);
            print "Dialog $dlgID\n";
            my $key = $dlgID;
            if (not exists $Titles{$key})
            {
                $Titles{$key} = ["", "", "", ""];
            }
            $Titles{$key}->[$I_STRING_ID] = $stringID;
        }
        elsif ($line =~ /dlg:id="(\w+)".+dlg:value="([^"]*)"/)
        {
            my ($controlID, $stringID) = ($1, $2);
            my $key = $dlgID . "." . $controlID;
            if (not exists $Strings{$key})
            {
                $Strings{$key} = ["", "", "", ""];
            }
            $Strings{$key}->[$I_STRING_ID] = $stringID;
        }
        elsif ($line =~ /dlg:titledbox dlg:id="(\w+)"/)
        {
            $titledBoxID = $1;
        }
        elsif ($line =~ /dlg:title dlg:value="([^"]*)"/)
        {
            my $stringID = $1;
            my $key = $dlgID . "." . $titledBoxID;
            if (not exists $Strings{$key})
            {
                $Strings{$key} = ["", "", "", ""];
            }
            $Strings{$key}->[$I_STRING_ID] = $stringID;
        }
    }
    close INFILE;
}

#-------------------------------------------------------------------------------
#
# sub read_strings_file
#
#-------------------------------------------------------------------------------
sub read_strings_file
{
    my ($infile) = @_;

    $infile =~ /DialogStrings_(\w\w)_\w\w.properties/;
    my $lang   = $1;
    my $i_lang = $I_EN;
    if ($lang eq 'en') {
        $i_lang = $I_EN;
    } elsif ($lang eq 'es') {
        $i_lang = $I_ES;
    } elsif ($lang eq 'fr') {
        $i_lang = $I_FR;
    }
    open (INFILE, "< $infile") || die "Couldn't open $infile";
    while (my $line = scalar(<INFILE>))
    {
        if ($line =~ /^(\d+)\.(\w+)\.(\w+)\.(?:Label|Text|Value)=(.*)$/)
        {
            my ($strNum, $dlgID, $controlID, $text) = ($1, $2, $3, $4);
            my $stringID = "$strNum.$dlgID.$controlID.Value";
            my $key = $dlgID . "." . $controlID;
            if (exists $Strings{$key} and $text ne '')
            {
                $Strings{$key}->[$i_lang] = $text;
            }
        }
        elsif ($line =~ /^(\d+)\.(\w+)\.Title=(.*)$/)
        {
            my ($strNum, $dlgID, $text) = ($1, $2, $3);
            my $stringID = "$strNum.$dlgID.Title";
            my $key = $dlgID;
            if (exists $Titles{$key})
            {
                $Titles{$key}->[$i_lang] = $text;
            }
        }
    }
    close INFILE;
}

#-------------------------------------------------------------------------------
# Write results to file
#-------------------------------------------------------------------------------

my $strNum = 0;
open (OUTFILE, "> $OUTFILE") || die "Couldn't open $OUTFILE for writing.";
foreach my $dlgID (sort keys %Titles)
{
    my ($oldTitleID, $titleEN, $titleES, $titleFR) = @{$Titles{$dlgID}};
    my $newTitleID = sprintf("\%d.\%s\.Title", $strNum++, $dlgID);
    print OUTFILE $newTitleID, "\t";
    print OUTFILE $oldTitleID, "\t";
    print OUTFILE $titleEN, "\t";
    print OUTFILE $titleES, "\t";
    print OUTFILE $titleFR, "\n";
    foreach my $stringKey (sort keys %Strings)
    {
        if ($stringKey =~ /^$dlgID/)
        {
            my ($oldStringID, $strEN, $strES, $strFR) = @{$Strings{$stringKey}};
            my $newStringID = sprintf("\%d.\%s\.Value", $strNum++, $stringKey);
            print OUTFILE $newStringID, "\t";
            print OUTFILE $oldStringID, "\t";   # may actually be EN string
            print OUTFILE $strEN, "\t";
            print OUTFILE $strES, "\t";
            print OUTFILE $strFR, "\n";
        }
    }
}
close OUTFILE;
