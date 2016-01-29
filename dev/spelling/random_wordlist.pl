
open (OUTFILE, "> out.txt");
foreach my $j (0 .. 20000)
{
    my $word = '';
    foreach my $i (0 .. 5)
    {
        my $num = int(rand(26)) + 97;
        my $c = chr($num);
        $word .= $c;
    }
    print OUTFILE $word, "\n";
}
close OUTFILE;
