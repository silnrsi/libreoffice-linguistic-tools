#-------------------------------------------------------------------------------
#
# dialog_strings_update.pl
#
# First run dialog_strings_read.pl to create dialog_strings.csv.
# This code reads the CSV file and makes a new LingToolsBasic with the changes.
#
# Created by Jim on March 22 2013
#
# 29-Mar-13 JDK  Add support for frame controls (titled boxes).
# 06-Mar-17 JDK  Use paths relative to the build directory.
#
#-------------------------------------------------------------------------------
use strict;
use File::Spec;

my $OUTFOLDER  = "LingToolsBasic_new\\";  # subfolder in the current folder
my $INFOLDER  = '..\\..\\LingToolsBasic';
my $INFILE_CSV = "dialog_strings.csv"; # in the current folder

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

my %Strings;   # keys are dialogID.fieldID
               # values are [stringID, stringEN, stringES, stringFR]
my %Titles;    # same but keys are just dialogID
my ($I_STRING_ID, $I_EN, $I_ES, $I_FR) = (0,1,2,3);

#-------------------------------------------------------------------------------
# Read files in the LingToolsBasic folder.
#-------------------------------------------------------------------------------

&read_csv_data;

mkdir $OUTFOLDER;
opendir(INFOLDER, $INFOLDER) || die "Couldn't open $INFOLDER for reading.";
readdir INFOLDER;   # .
readdir INFOLDER;   # ..
while (my $filename = readdir INFOLDER)
{
    if ($filename =~ /\.xdl$/)
    {
        &handle_dialog_file($filename);
    }
}
&write_strings_file;
exit;

#-------------------------------------------------------------------------------
#
# sub read_csv_data
#
#-------------------------------------------------------------------------------
sub read_csv_data
{
    open (INFILE, "< $INFILE_CSV") || die "Couldn't open $INFILE_CSV";
    while (my $line = scalar(<INFILE>))
    {
        $line =~ /^(.*)\t(.*)\t(.*)\t(.*)\t(.*)$/;
        my ($stringID, undef, $strEN, $strES, $strFR) = ($1, $2, $3, $4, $5);
        if ($stringID =~ /^(\d+)\.(\w+)\.(\w+)\.Value$/)
        {
            my (undef, $dlgID, $controlID) = ($1, $2, $3);
            my $stringKey = $dlgID . '.' . $controlID;
            $Strings{$stringKey} = ["", $strEN, $strES, $strFR];
        }
        elsif ($stringID =~ /^(\d+)\.(\w+)\.Title$/)
        {
            my (undef, $dlgID) = ($1, $2);
            $Titles{$dlgID} = ["", $strEN, $strES, $strFR];
        }
        else
        {
            print "Error; continuing...\n";
            next;
        }
    }
    close INFILE;

    ## Determine the new string IDs

    my $strNum = 0;
    foreach my $dlgID (sort keys %Titles)
    {
        my $newTitleID = sprintf("\%d.\%s\.Title", $strNum++, $dlgID);
        $Titles{$dlgID}->[$I_STRING_ID] = $newTitleID;
        foreach my $stringKey (sort keys %Strings)
        {
            if ($stringKey =~ /^$dlgID\./)
            {
                my $newStringID = sprintf("\%d.\%s\.Value",
                                          $strNum++, $stringKey);
                $Strings{$stringKey}->[$I_STRING_ID] = $newStringID;
            }
        }
    }
}

#-------------------------------------------------------------------------------
#
# sub handle_dialog_file
#
#-------------------------------------------------------------------------------
sub handle_dialog_file
{
    my ($filename) = @_;

    my $infilepath  = File::Spec->catfile($INFOLDER,  $filename);
    my $outfilepath = File::Spec->catfile($OUTFOLDER, $filename);

    my $dlgID;
    my $titledBoxID;
    open (INFILE, "< $infilepath") || die "Couldn't open $infilepath";
    open (OUTFILE, "> $outfilepath") || die "Couldn't open $outfilepath";
    while (my $line = scalar(<INFILE>))
    {
        if ($line =~ /dlg:window.+dlg:id="(\w+)"/)
        {
            $dlgID = $1;
            print "Reading Dialog $dlgID\n";
            my $titleRef = "&amp;" . $Titles{$dlgID}->[$I_STRING_ID];
            $line =~ s/(dlg:title=)"([^"]+)"/$1"$titleRef"/;
        }
        elsif ($line =~ /dlg:titledbox dlg:id="(\w+)"/)
        {
            $titledBoxID = $1;
        }
        elsif ($line =~ /<dlg:title /)
        {
            my $stringKey = $dlgID . "." . $titledBoxID;
            if (exists $Strings{$stringKey}) # not all controls have dlg:value
            {
                my $stringRef = "&amp;" . $Strings{$stringKey}->[$I_STRING_ID];
                $line =~ s/(dlg:value=)"([^"]*)"/$1"$stringRef"/;
            }
        }
        elsif ($line =~ /dlg:id="(\w+)"/)
        {
            my $controlID = $1;
            my $stringKey = $dlgID . "." . $controlID;
            if (exists $Strings{$stringKey}) # not all controls have dlg:value
            {
                my $stringRef = "&amp;" . $Strings{$stringKey}->[$I_STRING_ID];
                $line =~ s/(dlg:value=)"([^"]*)"/$1"$stringRef"/;
            }
        }
        $line =~ s/(dlg:help-text=)"([^"]+)"/$1""/;
        print OUTFILE $line;
    }
    close OUTFILE;
    close INFILE;
}

#-------------------------------------------------------------------------------
#
# sub write_strings_file
#
#-------------------------------------------------------------------------------
sub write_strings_file
{
    my @Langs = ('', 'en_US','es_ES','fr_FR');
    foreach my $i_lang ($I_EN, $I_ES, $I_FR)
    {
        my $filename = "DialogStrings_" . $Langs[$i_lang] .  ".properties";
        my $outfile  = $OUTFOLDER . $filename;
        print "Writing $filename\n";
        open (OUTFILE, "> $outfile") || die "Couldn't open $outfile.";
        print OUTFILE "# Strings for Dialog Library LingToolsBasic\n";
        foreach my $dlgID (sort keys %Titles)
        {
            print OUTFILE $Titles{$dlgID}->[$I_STRING_ID], "=";
            print OUTFILE $Titles{$dlgID}->[$i_lang],      "\n";
            foreach my $stringKey (sort keys %Strings)
            {
                if ($stringKey =~ /^$dlgID\./)
                {
                    print OUTFILE $Strings{$stringKey}->[$I_STRING_ID], "=";
                    print OUTFILE $Strings{$stringKey}->[$i_lang],      "\n";
                }
            }
        }
        close OUTFILE;
    }
}
