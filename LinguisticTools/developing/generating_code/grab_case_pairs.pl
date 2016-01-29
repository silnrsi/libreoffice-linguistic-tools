################################################################################
#
# Filename: grab_case_pairs.pl
#
# Change History:
#   Created on 12-Dec-12 by Jim
#
# To generate part of Letters.py:
# Before running this script, download the
# latest Unicode database file UnicodeData.txt.
#
################################################################################
use strict;

my $FALSE  = 0;
my $TRUE   = 1;
my $EXISTS = 'e';

my $INFILE = "UnicodeData.txt";
my $OUTFILE = "letters_out2.py";
#my $BREAK_EVERY = 6;   # add newlines after every 6 letters
my $LINE_WIDTH = 80;   # 80 chars

my @CasePairCapitals;
my @CasePairSmalls;

#-------------------------------------------------------------------------------
# Read data from file
#-------------------------------------------------------------------------------

open (INFILE, "< $INFILE") || die "Couldn't open $INFILE";
while (my $line = scalar(<INFILE>))
{
    if ($line =~ /^([0-9A-F]{4});([A-Z]+) CAPITAL LETTER ([A-Z]+);/)
    {
        my ($code, $script, $letter) = ($1, $2, $3, $4, $5);
        if ($line =~ /;([0-9A-F]{4});$/)
        {
            my $correspondingSmallCase = $1;
            if ($correspondingSmallCase ne '') {
                push @CasePairCapitals, $code;
                push @CasePairSmalls, $correspondingSmallCase;
            }
        }
    }
}
close INFILE;

#-------------------------------------------------------------------------------
# Write results to file
#-------------------------------------------------------------------------------

open (OUTFILE, "> $OUTFILE") || die "Couldn't open $OUTFILE for writing.";
print OUTFILE "    CASE_CAPITALS = [\n";
&output_codelist(\*OUTFILE, 12, \@CasePairCapitals);
print OUTFILE "    ]\n\n";
print OUTFILE "    # lower case equivalent of CaseCapital at same index\n";
print OUTFILE "    CASE_LOWER = [\n";
&output_codelist(\*OUTFILE, 12, \@CasePairSmalls);
print OUTFILE "    ]\n\n";
close OUTFILE;

#-------------------------------------------------------------------------------
sub output_codelist
{
    my ($filehandle, $indentSize, $codelist_ref) = @_;

    print $filehandle " " x $indentSize;
    my @codeList = @$codelist_ref;
    my $line_x = $indentSize; # how far to the right we are in printing the line
    foreach my $i (0 .. $#codeList) {
        my $out_str = "u\"\\u" . $codeList[$i] . "\"";
        if ($i < $#codeList) { $out_str .= "," }
        $line_x += length($out_str);
        if ($line_x >= $LINE_WIDTH) {
            print $filehandle "\n", " " x $indentSize;
            $line_x = $indentSize + length($out_str);
        }
        print $filehandle $out_str;
    }
}

