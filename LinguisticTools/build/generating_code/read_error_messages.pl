################################################################################
#
# read_error_messages.pl
#
# Reads OOoLT code and outputs all possible error messages.
# Also outputs all existing translations given in Locale.py.
# Outputs "NO" if a message is in Locale.py but not used elsewhere,
# in which case it can probably be removed from Locale.py.
# The resulting list can be translated manually and added to Locale.py.
#
# New dialog fields to localize will be shown towards the bottom of this file:
# LingToolsBasic/DialogStrings_es_ES.properties
# These also need to be translated manually.
# For any non-ASCII characters, put them in the properties file as "\u" plus
# four-digit hex unicode value.
#
# Addons.xcu also contains localized text. So the places to check are:
# - menus
# - dialog strings
# - messages in python code
#
# There are a couple of error messages in Basic code. Those could be localized
# by adding Basic code similar to lingt.Utils.Locale.Locale.__init__().
#
# Created by Jim on Oct 30 2010
#
# 30-Nov-12 JDK  Recurse subdirectories.
# 18-Mar-13 JDK  Make it work on Linux.
# 06-Mar-17 JDK  Use paths relative to the build directory.
#
################################################################################
use strict;
use File::Spec;

my $OUTFOLDER = ".\\";  # the current folder
my $INFOLDER_BASEPATH  = '..\\..\\pythonpath\\lingt\\';
my $OS = $^O;  # linux or MSWin32
print "Running in $OS\n";
if ($OS eq 'linux') {
    $OUTFOLDER         =~ s!\\!/!g;
    $INFOLDER_BASEPATH =~ s!\\!/!g;
}
my $OUTFILE = $OUTFOLDER . "read_error_messages-out.csv";

my $TRUE   = 1;
my $FALSE  = 0;
my $EXISTS = 'e';

## Get list of files

my @Infiles;
&recurse_subdirs($INFOLDER_BASEPATH);

sub recurse_subdirs
{
    my ($infolder) = @_;
    my @fileList = ();
    opendir(INFOLDER, $infolder) || die "Couldn't open $infolder for reading.";
    readdir INFOLDER;   # .
    readdir INFOLDER;   # ..
    while (my $filename = readdir INFOLDER) {
        push @fileList, $filename;
    }
    foreach my $filename (@fileList) {
        my $fullpath = File::Spec->catfile($infolder, $filename);
        if (-d $fullpath) {
            &recurse_subdirs($fullpath);
        } elsif ($filename =~ /\.py$/ and not $filename =~ /init/) {
            push @Infiles, $fullpath;
        }
    }
}

## Read files to find the messages

my %Messages;
foreach my $filepath (@Infiles) {
    my ($volume,$directories,$filename) = File::Spec->splitpath( $filepath );
    print "\n", $filename;
    my $contents = '';
    open(INFILE, "< $filepath") or die "Couldn't read $filepath";
    while (my $line = scalar(<INFILE>))
    {
        $contents .= $line;
    }
    close INFILE;
    $contents = &concat_multiline_strs($contents);
    my $CALLS =
        '(?:getText|display|displayOkCancel|displayYesNoCancel|' .
        'Error|ChoiceProblem)';
    while ($contents =~ /\..*$CALLS\s*\(\r?\n?\s*"(.+)"/g) {
        $Messages{$1} = $EXISTS;
        print ".";
    }
    while ($contents =~ /\..*$CALLS\s*\(\r?\n?\s*'([^']+)'/g) {
        $Messages{$1} = $EXISTS;
        print ".";
    }
    while ($contents =~ /message = "([^"]+)"\r?\n(.*?)\..*$CALLS\(message/gs) {
        $Messages{$1} = $EXISTS;
        print ".";
    }
    while ($contents =~ /ProgressBar\(([^\)]+)\)/gs) {
        my $args = $1;
        print "[ProgressBar($args)]";
        if ($args =~ /"([^"]+)"$/) {
            $Messages{$1} = $EXISTS;
            print ".";
        }
    }
    if ($contents =~ /message = "([^"]+)"\r?\n.*?message \+= "([^"]+)"/s) {
        $Messages{$1 . $2} = $EXISTS;
        print ".";
    }
}
print "\n";

## Find translations in Locale.py

my %TranslatedExprs;
my $infilepath = File::Spec->catfile($INFOLDER_BASEPATH, "Utils", "Locale.py");
print "reading $infilepath\n";
my $contents = '';
open(INFILE, "< $infilepath") or die "Couldn't read $infilepath";
while (my $line = scalar(<INFILE>)) {
    $contents .= $line;
}
close INFILE;
$contents =~ / translations = \{(.+?)\}\r?\n/s;
my $translations = $1;
$translations = &concat_multiline_strs($translations);
$translations =~ s/\{\r?\n/\{ /g;
$translations =~ s/:\r?\n/: /g;
$translations =~ s/",\r?\n/", /g;
while ($translations =~
       /"([^"]+)" : \{\s+'es' :\s+"([^"]*)",\s+'fr' :\s+"([^"]*)",/gm)
{
    my ($en, $es, $fr) = ($1, $2, $3);
    $TranslatedExprs{$en} = $es . "|" . $fr;
    print $en, "\n";
}

## Organize results

my %Results;
print "Messages: " . scalar(%Messages) . "\n";
foreach my $msg (keys %Messages) {
    $Results{$msg}{used} = $TRUE;
    if (exists $TranslatedExprs{$msg}) {
        $Results{$msg}{tx} = $TranslatedExprs{$msg};
    }
}
print "Translated Exprs: " . scalar(%TranslatedExprs) . "\n";
foreach my $msg (keys %TranslatedExprs) {
    if (not exists $Messages{$msg}) {
        $Results{$msg}{used} = $FALSE;
        $Results{$msg}{tx}   = $TranslatedExprs{$msg};
    }
}

## Write results

open (OUTFILE, "> $OUTFILE") or die "Couldn't open $OUTFILE.";
foreach my $msg (sort keys %Results) {
    my $result = $Results{$msg};
    if ($result->{used}) {
        print OUTFILE "YES|";
    } else {
        print OUTFILE "NO|";
    }
    print OUTFILE $msg, "|";
    if (exists $result->{tx}) {
        print OUTFILE $result->{tx};
    }
    print OUTFILE "\n";
}
print "Finished!\n";

# Change multiline python string literals into a single line.
sub concat_multiline_strs
{
    my ($multiline_string) = @_;
    $multiline_string =~ s/u"/"/g;
    $multiline_string =~ s/u'/'/g;
    $multiline_string =~ s/"\s*\+\s*\\?\r?\n\s*"//g;
    $multiline_string =~ s/'\s*\+\s*\\?\r?\n\s*'//g;
    $multiline_string =~ s/"\s*\\?\r?\n\s*"//g;
    $multiline_string =~ s/'\s*\\?\r?\n\s*'//g;
    return $multiline_string;
}
