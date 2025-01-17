import sys
from sacred import Experiment
import yaml
import time 
import os
method, task, taskid, wandb_project, module = sys.argv[1:]
ex = Experiment("ProtoNet", save_git_info=False)

@ex.config
def config():
    config_dict = {}

    #if training CLIP, set to True
    config_dict["load_pretrained"] = True
    #if training, set to False
    config_dict["is_test"] = False
    if config_dict["is_test"]:
        #if testing, specify the total rounds of testing. Default: 5
        config_dict["num_test"] = 5
        config_dict["load_pretrained"] = True
        #specify pretrained path for testing.
    if config_dict["load_pretrained"]:
        config_dict["pre_trained_path"] = None
        #only load the backbone.
        config_dict["load_backbone_only"] = False
        
    #Specify the model name, which should match the name of file
    #that contains the LightningModule
    config_dict["model_name"] = module
 
    

    #whether to use multiple GPUs
    multi_gpu = False
    if config_dict["is_test"]:
        multi_gpu = False
    #The seed
    seed = 10
    config_dict["seed"] = seed

    #The logging dirname: logdir/exp_name/
    log_dir = "./results/"
    exp_name = f"{method}/{task}"
    # exp_name = os.path.join(branch, exp_name)
    
    #Three components of a Lightning Running System
    trainer = {}
    data = {}
    model = {}


    ################trainer configuration###########################


    ###important###

    #debugging mode
    trainer["fast_dev_run"] = False

    if multi_gpu:
        trainer["accelerator"] = "ddp"
        trainer["sync_batchnorm"] = True
        trainer["gpus"] = [2,3]
        trainer["plugins"] = [{"class_path": "plugins.modified_DDPPlugin"}]
    else:
        trainer["accelerator"] = None
        trainer["gpus"] = [0]
        trainer["sync_batchnorm"] = False
    
    # whether resume from a given checkpoint file
    trainer["resume_from_checkpoint"] = None # example: "../results/ProtoNet/version_11/checkpoints/epoch=2-step=1499.ckpt"

    # The maximum epochs to run
    trainer["max_epochs"] = 60

    # potential functionalities added to the trainer.
    trainer["callbacks"] = [{"class_path": "pytorch_lightning.callbacks.LearningRateMonitor", 
                  "init_args": {"logging_interval": "step"}
                  },
                {"class_path": "pytorch_lightning.callbacks.ModelCheckpoint",
                  "init_args":{"verbose": True, "save_last": True, "monitor": "val/acc", "mode": "max"}
                },
                {"class_path": "callbacks.SetSeedCallback",
                 "init_args":{"seed": seed, "is_DDP": multi_gpu}
                }]

    ###less important###
    num_gpus = trainer["gpus"] if isinstance(trainer["gpus"], int) else len(trainer["gpus"])
    trainer["logger"] = {"class_path":"pytorch_lightning.loggers.WandbLogger",
                        "init_args": {"save_dir": os.path.join(log_dir, exp_name), "log_model": True, 
                            "project": wandb_project,"name": f"{method}/{task}/{taskid}", "id": taskid}}
    trainer["replace_sampler_ddp"] = False

    

    ##################shared model and datamodule configuration###########################

    #important
    per_gpu_train_batchsize = 4
    train_shot = 5
    test_shot = 1

    #less important
    per_gpu_val_batchsize = 8
    per_gpu_test_batchsize = 8
    train_way = 5
    val_way = 5
    test_way = 5
    val_shot = 1
    num_query = 15

    ##################datamodule configuration###########################

    #important

    #The name of dataset, which should match the name of file
    #that contains the datamodule.
    data["train_dataset_name"] = "miniImageNet_clip"
    data["train_data_root"] = "../data/libfewshot/miniImageNet"

    data["val_test_dataset_name"] = "miniImageNet_clip"
    data["val_test_data_root"] = "../data/libfewshot/miniImageNet"

    # FIXME: add test data path
    data["test_dataset_name"] = "miniImageNet_clip"
    data["test_data_root"] = "../data/libfewshot/miniImageNet"

    #determine whether meta-learning.
    data["is_meta"] = True
    data["train_num_workers"] = 8
    #the number of tasks
    data["train_num_task_per_epoch"] = 1000
    data["val_num_task"] = 1000
    data["test_num_task"] = 2000
    
    
    #less important
    data["train_batchsize"] = num_gpus*per_gpu_train_batchsize
    data["val_batchsize"] = num_gpus*per_gpu_val_batchsize
    data["test_batchsize"] = num_gpus*per_gpu_test_batchsize
    data["test_shot"] = test_shot
    data["train_shot"] = train_shot
    data["val_num_workers"] = 8
    data["is_DDP"] = True if multi_gpu else False
    data["train_way"] = train_way
    data["val_way"] = val_way
    data["test_way"] = test_way
    data["val_shot"] = val_shot
    data["num_query"] = num_query
    data["drop_last"] = False

    ##################model configuration###########################

    #important

    #The name of feature extractor, which should match the name of file
    #that contains the model.
    model["backbone_name"] = "ViT_B_32_clip"  # FIXME
    #the initial learning rate
    model["lr"] = 0.00005*data["train_batchsize"]/4


    #less important
    model["train_way"] = train_way
    model["val_way"] = val_way
    model["test_way"] = test_way
    model["train_shot"] = train_shot
    model["val_shot"] = val_shot
    model["test_shot"] = test_shot
    model["num_query"] = num_query
    model["train_batch_size_per_gpu"] = per_gpu_train_batchsize
    model["val_batch_size_per_gpu"] = per_gpu_val_batchsize
    model["test_batch_size_per_gpu"] = per_gpu_test_batchsize
    model["weight_decay"] = 5e-4
    #The name of optimization scheduler
    model["decay_scheduler"] = "cosine"
    model["optim_type"] = "sgd"
    #cosine or euclidean
    model["metric"] = "cosine"
    model["scale_cls"] = 10.
    model["normalize"] = True
    

    config_dict["trainer"] = trainer
    config_dict["data"] = data
    config_dict["model"] = model



# @ex.automain
def main(_config):
    config_dict = _config["config_dict"]
    file_ = 'config/config.yaml'
    stream = open(file_, 'w')
    yaml.safe_dump(config_dict, stream=stream,default_flow_style=False)

if __name__ == "__main__":
    _config = config()
    main(_config)