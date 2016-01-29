
$line = "314F;HANGUL LETTER A;";
if ($line =~
  /^([0-9A-F]{4});([A-Z]+)( CAPITAL| SMALL)? LETTER( FINAL)? ([A-Z]+);/)
{
    my ($code, $script, $case, $final, $letter) = ($1, $2, $3, $4, $5);
    print <<__1__;
code $code, script $script, case $case, final $final, letter $letter
__1__

}
exit;

my %Indic = (
    'DEVANAGARI' => $EXISTS,
    'TAMIL' => $EXISTS,
    'TELEGU' => $EXISTS,
    'GUJARATI' => $EXISTS,
    'BENGALI' => $EXISTS,
    "GURMUKHI" => $EXISTS,
    "KANNADA" => $EXISTS,
    "MALAYALAM" => $EXISTS,
    "ORIYA" => $EXISTS,
);
if (exists $Indic{"TAMIL"}) {
    print "yes\n";
} else {
    print "no\n";
}
exit;

my $cons_or_vow  = 'vow';
my $initial_only = 1;
if ($cons_or_vow ne '') {
    if ($cons_or_vow eq 'cons' and not $initial_only) {
        print "any cons\n";
    } elsif ($cons_or_vow eq 'cons' and $initial_only) {
        print "WI cons\n";
    } elsif ($cons_or_vow eq 'vow' and not $initial_only) {
        print "any vow\n";
    } elsif ($cons_or_vow eq 'vow' and $initial_only) {
        print "WI vow\n";
    } else {
        die "Logic mistake\n";
    }
}

exit;

#$line = "0915;DEVANAGARI LETTER KA;";
#$line = "0BE8;LATIN SMALL LETTER K;";
$line = "314F;HANGUL LETTER A;";


#if ($line =~ /(\d\d\d\d);([A-Z]+)(?: CAPITAL| SMALL)? LETTER ([A-Z]+)/)
#if ($line =~ /^([[:xdigit:]]{4});([A-Z]+)(?: CAPITAL| SMALL)? LETTER ([A-Z]+)/)
#if ($line =~ /^([A-Z0-9]{4});([A-Z]+)(?: CAPITAL| SMALL)? LETTER ([A-Z]+)/)
if ($line =~ /^([0-9A-F]{4});([A-Z]+)( CAPITAL| SMALL)? LETTER ([A-Z]+;)/)
{
    print join(",", ($1, $2, $3, $4)), "\n";
    $letter = $4;
    if ($letter =~ /^[A|E|I|O|U|Y]+$/) {
        print "matched $letter";
    } else {
        print "didn't match $letter";
    }
}
else
{
    print "Did not match (1)\n";
}

