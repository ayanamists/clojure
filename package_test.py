import subprocess
import re
import tempfile
import shutil
import os
import os.path as p
import stat

def taie_trans(original, target):
    current_dir = p.dirname(p.realpath(__file__))
    app_dir = p.join(p.dirname(p.dirname(current_dir)), 'app')
    subprocess.run(f"gradle taieTrans --args='{original} {target}'", shell=True, cwd=app_dir)

def relative_cp(root, cp):
    return [ p.relpath(i, start=root) for i in cp ]

def write_runfile(root, path, cp):
    props = "'-Dclojure.test-clojure.exclude-namespaces=#{clojure.test-clojure.compilation.load-ns clojure.test-clojure.ns-libs-load-later}' -Dclojure.compiler.direct-linking=true"
    cp_str = ':'.join(relative_cp(root, cp))
    test_command1 = f"java -cp {cp_str} {props} clojure.main src/script/run_test.clj"
    test_command2 = f"java -cp {cp_str} {props} clojure.main src/script/run_test_generative.clj"
    with open(path, 'w+') as f:
        f.writelines([test_command1, '\n', test_command2])

    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC)


current_dir = p.dirname(p.realpath(__file__))
cp_out = subprocess.check_output(['mvn', 'dependency:build-classpath', '-DincludeScope=test', '-Dmdep.outputFilterFile=true'])
cp_list = re.search('classpath=(.*)', cp_out.decode('utf-8')).group(1).split(':')

subprocess.run('mvn -Plocal -Dmaven.test.skip=true package'.split(' '))
subprocess.run(['mvn', 'test-compile'])

tmp_dir = tempfile.mkdtemp()
lib_dir = p.join(tmp_dir, 'lib')
os.mkdir(lib_dir)

test_cp = [] # test_cp[0] is target
test_cp.append(shutil.copy('./clojure.jar', tmp_dir))

src_dir = p.join(tmp_dir, 'src')
shutil.copytree(p.join(current_dir, 'src'), src_dir)

for cp in cp_list:
    test_cp.append(shutil.copy(cp, lib_dir))
target_dir = p.join(tmp_dir, 'target')
os.mkdir(target_dir)
test_cp.append(shutil.copytree(p.join(current_dir, 'target/test-classes'), p.join(tmp_dir, 'target/test-classes')))
test_cp.append(shutil.copytree(p.join(current_dir, 'test'), p.join(tmp_dir, 'test')))
shutil.copy(p.join(current_dir, 'readme.txt'), tmp_dir)

taie_trans(p.join(tmp_dir, 'clojure.jar'), p.join(tmp_dir, 'clojure-taie-trans.jar'))
write_runfile(tmp_dir, p.join(tmp_dir, 'run_original.sh'), test_cp)
test_taie_cp = [i for i in test_cp]
test_taie_cp[0] = p.join(tmp_dir, 'clojure-taie-trans.jar')
write_runfile(tmp_dir, p.join(tmp_dir, 'run_taie_trans.sh'), test_taie_cp)

subprocess.run(['tree', tmp_dir, '-L', '2'])
subprocess.run(['zip', '-r', 'test.zip', '.'], cwd=tmp_dir)
shutil.copy(p.join(tmp_dir, 'test.zip'), current_dir)
shutil.rmtree(tmp_dir)

print('Package success')
