################################################################################
#
# assimilate.pl
#
# Reads in OOoLT python scripts and assimilates them into individual
# executable files.
#
# To remove ^M newlines using GVim, type :%s Ctrl+V Ctrl+M $//c
#
# Created by Jim on Sept 22 2010
#
#   24-Sep-10 JDK  Only import standard modules once. 
#   01-Oct-10 JDK  Handle imported package modules (from package import module).
#   28-Jun-11 JDK  Modify for Linux.
#   26-Oct-12 JDK  Handle deeper package subfolders.
#
################################################################################
use strict;

my $OS = $^O;   # linux or MSWin32
print "Running in $OS\n";
my $SEP = "\\";
#my $ENDL = "\r\n";
my $ENDL = "\n";
if ($OS eq 'linux') {
    $SEP = "/";
}

#my $OUTFOLDER = "." . $SEP;  # the current folder
my $OUTFOLDER = 'D:\Jim\computing\Office\OOo Linguistic Tools' .
                '\dev\extensions\catch silent errors' .
                '\developing\assimilated code\\';
my $INFOLDER_BASEPATH = 'D:\Jim\computing\Office\OOo Linguistic Tools' .
                     '\dev\extensions\catch silent errors\pythonpath\lingt\\';
if ($OS eq 'linux') {
    $OUTFOLDER         =~ s!\\!/!g;
    $INFOLDER_BASEPATH =~ s!\\!/!g;
    $OUTFOLDER         =~ s!^D:!/media/winD!;
    $INFOLDER_BASEPATH =~ s!^D:!/media/winD!;
}
my $TRUE   = 1;
my $FALSE  = 0;
my $EXISTS = 'e';

my $INFOLDER_PATH = $INFOLDER_BASEPATH . "UI" . $SEP;
opendir(INFOLDER, $INFOLDER_PATH) ||
    die "Couldn't open $INFOLDER_PATH for reading.";
readdir INFOLDER;   # .
readdir INFOLDER;   # ..
my $filename;
my @ToplevelFiles;
my %ImportedPackages;
while (my $filename = readdir INFOLDER) {
    if ($filename =~ /\.py$/) {
        my $toplevelFile = $INFOLDER_PATH . $filename;
        my $exportedScriptsDecl = &getExportedScripts($toplevelFile);
        if ($exportedScriptsDecl ne '')
        {
            my %FilesContent     = ();
            my %FileDependencies = ();
            my @FilesList        = ();
            %ImportedPackages = ();
            print "Building $toplevelFile\n";
            &getNeededFiles (
                $toplevelFile, \%FilesContent, \@FilesList, \%FileDependencies);
            my $outfile = $OUTFOLDER . $filename;
            open (OUTFILE, "> $outfile") or die "Couldn't open $outfile.";
            print OUTFILE "#!/usr/bin/python\n# -*- coding: Latin-1 -*-\n\n";
            print OUTFILE "## Import standard modules\n";
            if (exists $ImportedPackages{"import uno"}) {
                print OUTFILE "import uno\n";
                delete $ImportedPackages{"import uno"}
            }
            foreach my $importedPackage (sort keys %ImportedPackages) {
                print OUTFILE $importedPackage . "\n";
            }
            print OUTFILE "\n";
            &sortFiles(\@FilesList, \%FileDependencies);
            foreach my $filepath (@FilesList) {
                my $fileContents = $FilesContent{$filepath};
                print OUTFILE "#" . '-' x 79 . "\n";
                print OUTFILE "# Start of " . &getFilename($filepath) . "\n";
                print OUTFILE "#" . '-' x 79 . "\n\n";
                print OUTFILE $fileContents;
                print OUTFILE "#" . '-' x 79 . "\n";
                print OUTFILE "# End of " . &getFilename($filepath) . "\n";
                print OUTFILE "#" . '-' x 79 . "\n\n";
            }
            print OUTFILE "\n";
            print OUTFILE "# Exported Scripts:\n";
            print OUTFILE $exportedScriptsDecl;
            close OUTFILE;
            print "Finished building $toplevelFile\n\n";
        }
    }
}
close INFOLDER;
print "Finished!\n";

sub getExportedScripts
{
    my ($filepath) = @_;
    my $exportedScriptsDecl = '';
    my $fileContents = '';
    open(INFILE, "< $filepath") or die "Couldn't read $filepath";
    while (my $line = scalar(<INFILE>))
    {
        $line =~ s/\r?\n$//;  # remove Win or Unix line ending chars
        if ($line =~ /^g_exportedScripts/) {
            $exportedScriptsDecl = $line . $ENDL;
        }
    }
    close INFILE;
    return $exportedScriptsDecl;
}

sub getNeededFiles
{
    my ($fileToCheck, $FilesContentRef, $FilesList, $FileDepsRef) = @_;
    my $filename = &getFilename($fileToCheck);
    print "    Including $filename\n";
    open(INFILE, "< $fileToCheck") or die "Couldn't read $fileToCheck";
    my @importedFiles;
    my @referencedModules;
    my $inHeader = $TRUE;
    my $fileContents;
    while (my $line = scalar(<INFILE>))
    {
        $line =~ s/\r?\n$//;  # remove Win or Unix line ending chars
        if ($line =~ /^import|^from/)
        {
            $inHeader = $FALSE;
            if ($line =~ /^from\s+lingt((?:\.\w+){1,2})\s+import (\w+)/)
            {
                my ($package, $filename) = ($1, $2);
                $package =~ s/^\.//;
                print "package '$package', filename '$filename'\n";
                my $package_path = $package;
                $package_path =~ s/\./$SEP/;
                my @filenames = split(', ?', $filename);
                foreach $filename(@filenames) {
                    my $filepath = $INFOLDER_BASEPATH . $package_path . $SEP .
                                   $filename . ".py";
                    if (-e $filepath) {
                        push @referencedModules, $filename
                    }
                    push @importedFiles, [$package, $filename];
                }
            }
            elsif ($line =~ /lingt((?:\.\w+){1,2})\.(\w+)/)
            {
                my ($package, $filename) = ($1, $2);
                $package =~ s/^\.//;
                print "package '$package', filename '$filename'\n";
                push @importedFiles, [$package, $filename];
            }
            else
            {
                $line =~ s/  / /g;
                $ImportedPackages{$line} = $EXISTS;
            }
        }
        elsif ($inHeader)
        {
            if ($line =~ /^class / or $line =~ /^def /)
            {
                $inHeader = $FALSE;
                $fileContents .= $line . $ENDL;
            }
            else
            {
                next; ## Skip this line
            }
        }
        elsif ($line =~ /^g_exportedScripts/)
        {
            next; ## Skip this line
        }
        else
        {
            $line =~ s/lingt(?:\.\w+){2,3}\.(\w+)/$1/;
            foreach my $moduleName (@referencedModules)
            {
                $line =~ s/(\W)$moduleName\./$1/g;
            }
            $fileContents .= $line . $ENDL;
        }
    }
    close INFILE;
    $FilesContentRef->{$fileToCheck} = $fileContents;
    push @$FilesList, $fileToCheck;
    foreach my $rec (@importedFiles) {
        my ($package, $filename) = @$rec;
        $package =~ s/\./$SEP/;
        my $nextFileToCheck =
            $INFOLDER_BASEPATH . $package . $SEP . $filename . ".py";
        if (not -e $nextFileToCheck) {
            $nextFileToCheck = $INFOLDER_BASEPATH . $package . ".py";
        }
        push @{$FileDepsRef->{$fileToCheck}}, $nextFileToCheck;
        if (not exists $FilesContentRef->{$nextFileToCheck})
        {
            &getNeededFiles(
                $nextFileToCheck, $FilesContentRef, $FilesList, $FileDepsRef);
        }
    }
}

sub getFilename
{
    my ($filepath) = @_;
    $filepath =~ /([a-zA-Z_]+\.py)/;
    return $1;
}

# Sort files according to dependencies.
# Modifies the original list.
sub sortFiles
{
    my ($filesList, $fileDeps) = @_;

    my @listSorted = ();
    foreach my $filepath (@$filesList)
    {
        if (not grep {$_ eq $filepath} @listSorted)
        {
            # not in the list yet, so let's add it at the end
            push @listSorted, $filepath;
        }
        foreach my $dep (@{$fileDeps->{$filepath}})
        {
            &moveBefore(\@listSorted, $dep, $filepath);
        }
    }
    @$filesList = @listSorted;
}
# Move elem1 to just before elem2 in the list.
# Elem2 is required to be in the list already, but elem1 is optional.
# If elem1 is already earlier in the list than elem2, does nothing.
sub moveBefore
{
    my ($list, $elem1, $elem2) = @_;
    my $i1 = -1;    # index of elem1
    my $i2 = -1;    # index of elem2
    foreach my $i (0 .. $#$list) {
        if ($list->[$i] eq $elem1) {
            $i1 = $i;
        } elsif ($list->[$i] eq $elem2) {
            $i2 = $i;
        }
    }
    if ($i2 < 0) {
        print "couldn't find in list: $elem2\n";
        return
    }
    if ($i1 >= 0) {
        if ($i1 < $i2) {
            # no need to do anything
            return
        }
        splice @$list, $i1, 1;           # remove elem1 at original location
    }
    splice @$list, $i2, 0, $elem1;   # insert elem1 just before elem2
    print "moved up ", &getFilename($list->[$i2]), "\n";
}

