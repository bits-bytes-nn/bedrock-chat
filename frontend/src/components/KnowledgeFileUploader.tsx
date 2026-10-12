import React, { useCallback } from 'react';
import { BaseProps } from '../@types/common';
import { twMerge } from 'tailwind-merge';
import { BotFile } from '../@types/bot';
import { produce } from 'immer';
import { useTranslation } from 'react-i18next';
import { PiFile, PiTrash, PiWarningCircleFill } from 'react-icons/pi';
import ButtonIcon from './ButtonIcon';
import { AxiosError } from 'axios';
import Progress from './Progress';
import useBot from '../hooks/useBot';
import { create } from 'zustand';
import { ulid } from 'ulid';
import ButtonFileChoose from './ButtonFileChoose';
import {
  CONVERTIBLE_FILE_EXTENSIONS,
  isConvertibleFile,
  maxConvertibleFileSizeMb,
} from '../constants/supportedAttachedFiles';

type Props = BaseProps & {
  botId: string;
  files: BotFile[];
  onAdd: (files: BotFile[]) => void;
  onUpdate: (files: BotFile[]) => void;
  onDelete: (files: BotFile[], deletedFilename: string) => void;
  disabled?: boolean;
};

const SUPPORTED_FILES = [
  '.txt',
  '.md',
  '.xlsx',
  '.docx',
  '.pdf',
  '.csv',
  // Converted into a text file after the upload.
  ...CONVERTIBLE_FILE_EXTENSIONS,
];

const KnowledgeFileUploaderState = create<{
  files: BotFile[];
  getFiles: () => BotFile[];
  setFiles: (f: BotFile[]) => void;
}>((set, get) => {
  return {
    files: [],
    getFiles: () => get().files,
    setFiles: (f) => {
      set(() => {
        return {
          files: f,
        };
      });
    },
  };
});

const KnowledgeFileUploader: React.FC<Props> = (props) => {
  const { t } = useTranslation();
  const { uploadFile } = useBot();
  const { getFiles: _getFiles, setFiles: _setFiles } =
    KnowledgeFileUploaderState();

  const uploadFiles = useCallback(
    (targetFiles: FileList) => {
      if (props.disabled) {return;}

      // Normalize file names that contain certain Japanese characters to avoid errors in the ECS Task.
      const renamedFiles: File[] = [];
      for (let i = 0; i < targetFiles.length; i++) {
        renamedFiles.push(
          new File([targetFiles[i]], targetFiles[i].name.normalize('NFC'), {
            type: targetFiles[i].type,
          })
        );
      }

      // Rows are identified by id: they can be removed or added while a long
      // conversion runs, which shifts their positions.
      const uids = renamedFiles.map(() => ulid());
      _setFiles(
        produce(props.files, (draft) => {
          renamedFiles.forEach((file, idx) => {
            const isSupportedFile = SUPPORTED_FILES.includes(
              '.' + file.name.split('.').slice(-1)[0].toLowerCase()
            );
            // A converted file is registered as `<filename>.txt`.
            const registeredNames = isConvertibleFile(file.name)
              ? [file.name, `${file.name}.txt`]
              : [file.name];
            const isDuplicatedFile = props.files.some((botFile) =>
              registeredNames.includes(botFile.filename)
            );
            const maxSizeMb = isConvertibleFile(file.name)
              ? maxConvertibleFileSizeMb(file.name)
              : undefined;
            const isTooLarge =
              maxSizeMb !== undefined && file.size > maxSizeMb * 1024 * 1024;

            if (isSupportedFile && !isDuplicatedFile && !isTooLarge) {
              draft.push({
                uid: uids[idx],
                filename: file.name,
                status: 'UPLOADING',
              });
            } else {
              draft.push({
                uid: uids[idx],
                filename: file.name,
                status: 'ERROR',
                errorMessage: isDuplicatedFile
                  ? t('bot.error.duplicatedFile')
                  : isTooLarge
                    ? t('error.attachment.fileSizeExceeded', {
                        maxSize: `${maxSizeMb} MB`,
                      })
                    : t('bot.error.notSupportedFile'),
              });
            }
          });
        })
      );
      props.onAdd(_getFiles());

      const updateFile = (uid: string, recipe: (file: BotFile) => void) => {
        _setFiles(
          produce(_getFiles(), (draft) => {
            const file = draft.find((f) => f.uid === uid);
            if (file) {
              recipe(file);
            }
          })
        );
        props.onUpdate(_getFiles());
      };

      renamedFiles.forEach((file, idx) => {
        const uid = uids[idx];
        if (_getFiles().find((f) => f.uid === uid)?.status === 'UPLOADING') {
          uploadFile(
            props.botId,
            file,
            (progress) => updateFile(uid, (f) => (f.progress = progress)),
            () => updateFile(uid, (f) => (f.status = 'CONVERTING'))
          )
            .then((filename) =>
              updateFile(uid, (f) => {
                f.filename = filename;
                f.status = 'UPLOADED';
              })
            )
            .catch((e: AxiosError | Error) => {
              console.error(e);
              updateFile(uid, (f) => {
                f.status = 'ERROR';
                f.errorMessage = e.message;
              });
            });
        }
      });
    },
    [_getFiles, _setFiles, props, t, uploadFile]
  );

  const onDragOver: React.DragEventHandler<HTMLDivElement> = useCallback(
    (e) => {
      e.preventDefault();
    },
    []
  );

  const onDrop: React.DragEventHandler<HTMLDivElement> = useCallback(
    (e) => {
      e.preventDefault();
      if (!props.disabled) {
        uploadFiles(e.dataTransfer.files);
      }
    },
    [uploadFiles, props.disabled]
  );

  const onDeleteFile = useCallback(
    (idx: number) => {
      if (props.disabled) {return;}
      
      const files = produce(props.files, (draft) => {
        draft.splice(idx, 1);
      });
      // Keep the copy that pending uploads update in sync.
      _setFiles(files);
      props.onDelete(files, props.files[idx].filename);
    },
    [_setFiles, props]
  );

  return (
    <>
      <div
        onDragOver={onDragOver}
        onDrop={onDrop}
        className={twMerge(
          'flex h-full w-full flex-col items-center justify-center gap-3 rounded border-4 border-gray text-dark-gray dark:text-light-gray',
          props.disabled && 'opacity-50 cursor-not-allowed',
          props.className
        )}>
        <div>
          {t('bot.label.dndFileUpload', {
            fileExtensions: SUPPORTED_FILES.join(','),
          })
            .split('\n')
            .map((s, idx) => (
              <div key={idx}>{s}</div>
            ))}
        </div>

        <ButtonFileChoose
          onChange={uploadFiles}
          accept={SUPPORTED_FILES.join(',')}
          disabled={props.disabled}>
          {t('bot.button.chooseFiles')}
        </ButtonFileChoose>
      </div>

      <div className="flex flex-col gap-1">
        {props.files.map((file, idx) => (
          <div key={idx} className="rounded border border-gray bg-white p-1 ">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 break-all px-1">
                <PiFile className="w-5" />
                <div>{file.filename}</div>
              </div>
              <div className="flex items-center gap-2">
                <div className="ml-auto whitespace-nowrap">
                  {file.status === 'UPLOADING' && (
                    <div className="text-sm text-dark-gray dark:text-light-gray">
                      {t('bot.label.fileUploadStatus.uploading')}
                      <Progress progress={file.progress ?? 0} />
                    </div>
                  )}
                  {file.status === 'CONVERTING' && (
                    <div className="text-sm text-dark-gray dark:text-light-gray">
                      {t('bot.label.fileUploadStatus.converting')}
                    </div>
                  )}
                  {file.status === 'UPLOADED' && (
                    <div className="text-sm font-bold text-dark-gray dark:text-light-gray">
                      {t('bot.label.fileUploadStatus.uploaded')}
                    </div>
                  )}
                  {file.status === 'ERROR' && (
                    <div className="flex items-center gap-1 text-sm font-bold text-red dark:text-red-400">
                      <PiWarningCircleFill />
                      {t('bot.label.fileUploadStatus.error')}
                    </div>
                  )}
                </div>
                <div>
                  <ButtonIcon
                    className="text-red dark:text-red-400"
                    disabled={
                      file.status === 'UPLOADING' ||
                      file.status === 'CONVERTING' ||
                      props.disabled
                    }
                    onClick={() => {
                      onDeleteFile(idx);
                    }}>
                    <PiTrash />
                  </ButtonIcon>
                </div>
              </div>
            </div>
            {file.errorMessage && (
              <div className="rounded border border-dark-gray bg-light-gray px-2 py-1 text-sm ">
                <div className="font-bold text-red dark:text-red-400">
                  {t('bot.label.uploadError')}
                </div>
                <div className="italic">{file.errorMessage}</div>
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
};

export default KnowledgeFileUploader;
