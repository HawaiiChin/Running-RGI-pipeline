from jug import TaskGenerator, bvalue
from jug.utils import jug_execute
import itertools

MAX_SEQ_CHUNKS = 1_000

@TaskGenerator
def split_seq_file(faa):
    from os import makedirs,path
    from fasta import fasta_iter
    import gzip
    makedirs('partials', exist_ok = True)
    cur_n = MAX_SEQ_CHUNKS + 1
    basename = path.basename(faa)
    ix = 0
    out = None
    partials = []
    for h, seq in fasta_iter(faa):
        if cur_n >= MAX_SEQ_CHUNKS:
            partials.append(f'partials/{basename}_block_{ix:04}.faa.gz')
            out = gzip.open(partials[-1], compresslevel = 1, mode = 'wt')
            cur_n = 0
            ix += 1
        out.write(f'>{h}\n{seq}\n')
        cur_n +=1
    out.close()
    return partials
   
@TaskGenerator
def run_rgi(faa):
    from os import makedirs
    import shutil 
    import subprocess
    import tempfile
    makedirs('partials.rgi', exist_ok = True)
    oname = faa.replace('partials', 'partials.rgi').replace('faa.gz', 'rgi.tsv')
    with tempfile.TemporaryDirectory as tdir:
        if faa.endswith('.gz'):
            import gzip
            faa_expanded = tdir + '/data.faa.gz'
            with gzip.open(faa, 'rb') as ifile, \
                open(faa_expanded, 'wb') as ofile:
                while True:
                    block = ifile.read(8192)
                    if not block:
                        break
                    ofile.write(block)
            faa = faa.expanded
        tmp_oname = tdir + '/RGI_output'
        subprocess.check_call([
            'rgi', 'main',
            '-t', 'protein',
            '-i', faa, 
            '-o', tmp_oname])
        shutil.copy(tmp_oname+ '.txt', oname)
    return oname
    
@TaskGenerator
def concat_partials(partials, oname):
    import pandas as pd
    partials = [pd.read_table(p, index_col =0, comment = '#') for p in partials]
    full = pd.concat(partials)
    full.to_csv(oname, sep='\t')
    return oname

splits = split_seq_file('data\GMGC.wastewater.fna.gz')

partials = []
for faa in (bvalue(splits)):
    partials.append(run_rgi(faa))

concat_partials(partials,'outputs/rgi.full.tsv.gz')
