// To change the supported text format files, change the extension list below.
export const TEXT_FILE_EXTENSIONS = [
  '.txt',
  '.py',
  '.ipynb',
  '.js',
  '.jsx',
  '.html',
  '.css',
  '.java',
  '.cs',
  '.php',
  '.c',
  '.cpp',
  '.cxx',
  '.h',
  '.hpp',
  '.rs',
  '.R',
  '.Rmd',
  '.swift',
  '.go',
  '.rb',
  '.kt',
  '.kts',
  '.ts',
  '.tsx',
  '.m',
  '.scala',
  '.rs',
  '.dart',
  '.lua',
  '.pl',
  '.pm',
  '.t',
  '.sh',
  '.bash',
  '.zsh',
  '.csv',
  '.log',
  '.ini',
  '.config',
  '.json',
  '.proto',
  '.yaml',
  '.yml',
  '.toml',
  '.lua',
  '.sql',
  '.bat',
  '.md',
  '.coffee',
  '.tex',
  '.latex',
];

// Supported non-text file extensions which can be handled on Converse API.
// Ref: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_DocumentBlock.html
export const NON_TEXT_FILE_EXTENSIONS = [
  '.pdf',
  '.doc',
  '.docx',
  '.xls',
  '.xlsx',
];

// Converted to text by the backend: presentations are parsed and recordings are
// transcribed with Amazon Transcribe.
export const CONVERTIBLE_FILE_EXTENSIONS = [
  '.pptx',
  '.mp3',
  '.mp4',
  '.wav',
  '.flac',
  '.ogg',
  '.amr',
  '.webm',
  '.m4a',
];
// Convertible files are uploaded to S3, so they are not limited by the request size.
// Presentations are parsed by the API, so they have a lower limit.
const MAX_PRESENTATION_FILE_SIZE_MB = 100;
const MAX_MEDIA_FILE_SIZE_MB = 500;

export const maxConvertibleFileSizeMb = (fileName: string): number =>
  fileName.toLowerCase().endsWith('.pptx')
    ? MAX_PRESENTATION_FILE_SIZE_MB
    : MAX_MEDIA_FILE_SIZE_MB;

/** Name of the text file that the backend writes for a converted file. */
export const convertedFileName = (fileName: string): string => `${fileName}.txt`;

export const isConvertibleFile = (fileName: string): boolean =>
  CONVERTIBLE_FILE_EXTENSIONS.some((extension) =>
    fileName.toLowerCase().endsWith(extension)
  );

export const SUPPORTED_FILE_EXTENSIONS = [
  ...TEXT_FILE_EXTENSIONS,
  ...NON_TEXT_FILE_EXTENSIONS,
  ...CONVERTIBLE_FILE_EXTENSIONS,
];

// Converse API limitations:
// You can include up to five documents. Each document’s size must be no more than 4.5 MB.
// Ref: https://awscli.amazonaws.com/v2/documentation/api/latest/reference/bedrock-runtime/converse.html
export const MAX_FILE_SIZE_MB = 4.5;
export const MB = 1024 * 1024;
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * MB;
export const MAX_ATTACHED_FILES = 5;
