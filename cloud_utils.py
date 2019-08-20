import sys, os

def exe(command, do_print=True):
    print(command)
    if do_print:
        print(os.popen(command).read())  # + ' >> ' + os.path.join(base_dir_res, 'log.txt')
    else:
        os.system(command + " > /dev/null")

def init_code(dropbox_key, base_res, base_dir_code, experiment_name, dataset=None, base_dir_dataset='datasets/'):
    print('init code')
    base_dir_res = os.path.join(base_res, experiment_name)
    if not os.path.exists(base_res):
        os.makedirs(base_res)
    base_dir_res_dropbox = '/results/' + experiment_name
    exe('pip install dropbox')

    if not os.path.exists(base_dir_dataset):
        os.makedirs(base_dir_dataset)
    if not os.path.exists(base_dir_code):
        os.makedirs(base_dir_code)
    import dropbox

    if not isinstance(dropbox_key, list):
        dropbox_key = [dropbox_key]
    dbx_list = [dropbox.Dropbox(key) for key in dropbox_key]
    dbx = dbx_list[0]
    sys.path.append(base_dir_code)
    import dropbox_utils
    dropbox_utils.recursive_download(dbx, base_dir_code, '/code/ML')
    dropbox_utils.recursive_download(dbx, base_dir_res, base_dir_res_dropbox)
    if dataset and "://" not in dataset:
        if len(dbx_list) > 1:
            dbx_dataset = dbx_list[1]  # dataset in another dropbox
        else:
            dbx_dataset = dbx
        dbx_dataset.files_download_to_file(os.path.join(base_dir_dataset, os.path.basename(dataset)), dataset)
        exe('unzip -o ' + os.path.join(base_dir_dataset, os.path.basename(dataset)) + ' -d ' + base_dir_dataset, False)
    if dataset and "://" in dataset:
        exe('wget -O ' + os.path.join(base_dir_dataset, 'db.zip') + ' "' + dataset + '"')
        # zip_file = glob.glob(os.path.join(base_dir_dataset, '*.zip'))[0]
        exe('unzip -o ' + os.path.join(base_dir_dataset, 'db.zip') + ' -d ' + base_dir_dataset, False)

    def callback(upload_checkpoint=False):
        print('callback')
        try:
            dropbox_utils.recursive_upload(dbx, os.path.join(base_dir_res, 'output'),
                                           os.path.join(base_dir_res_dropbox, 'output'))

            if upload_checkpoint:
                dropbox_utils.recursive_upload(dbx, os.path.join(base_dir_res, 'checkpoints'),
                                               os.path.join(base_dir_res_dropbox, 'checkpoints'))
        except Exception as e:
            print('recursive upload failed', e)

    return dbx, callback, base_dir_res


def start_train(dropbox_key, base_res, base_dir_code, experiment_name,
                program, net_params, additional_args=[], func='main',
                upload_ckp=False, custom_db=None, base_dir_dataset='datasets/'):
    if custom_db:
        dataset_dropbox = custom_db
    else:
        if program == 'autoencoders':
            dataset_dropbox = '/datasets/faces.zip'
        elif program == 'cifar10':
            dataset_dropbox = None
        else:
            dataset_dropbox = None
    dbx, callback, base_dir_res = init_code(dropbox_key, base_res, base_dir_code, experiment_name,
                                            dataset=dataset_dropbox, base_dir_dataset=base_dir_dataset)
    if program == 'autoencoders':
        import autoencoders.cnn_autoencoders as prog
    elif program == 'cifar10':
        import classification.train_cifar10 as prog
    elif program == 'RL':
        exe('apt install cmake libopenmpi-dev python3-dev zlib1g-dev --assume-yes')
        exe("git clone https://github.com/openai/baselines.git /baselines ; cd /baselines ; pip install -e .")
        sys.path.append('/baselines')
        exe("pip install gym[all] -U")
        exe("pip install gym[atari] -U")
        exe("pip install vel -U")
        exe("apt install ffmpeg --assume-yes")
        import RL.agent.run as prog
    else:
        raise NotImplementedError
    if program == 'RL': #fixme
        args = additional_args + ['--res_dir', os.path.join(base_dir_res, 'output')]
    else:
        list_args = additional_args + ['--dataset', base_dir_dataset,
                                       '--res_dir', os.path.join(base_dir_res, 'output'),
                                       '--checkpoint', os.path.join(base_dir_res, 'checkpoints', 'checkpoint.pth')]

        args = prog.get_args(list_args)
        args.net_params.update(net_params)
    func_to_run = getattr(prog, func)
    func_to_run(args, callback, upload_ckp)
