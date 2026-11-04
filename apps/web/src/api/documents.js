import { apiFetch } from "./client.js";

/**
 * Lists all documents in the organization.
 * @returns {Promise<Array<{ id: string, title: string, file_type: string, status: string, chunk_count: number }>>}
 */
export async function listDocuments() {
  return apiFetch("/documents");
}

/**
 * Fetches single document details.
 * @param {string} id
 * @returns {Promise<any>}
 */
export async function getDocument(id) {
  return apiFetch(`/documents/${id}`);
}

/**
 * Retrieves chunk outline and previews for a document.
 * @param {string} id
 * @returns {Promise<Array<{ id: string, chunk_index: number, section_title: string, section_path: string, content: string, token_count: number }>>}
 */
export async function getDocumentChunks(id) {
  return apiFetch(`/documents/${id}/chunks`);
}

/**
 * Uploads a file (PDF, text, HTML) to the ingestion pipeline.
 * @param {File} file
 * @param {string} [title]
 * @returns {Promise<any>}
 */
export async function uploadDocument(file, title) {
  const formData = new FormData();
  formData.append("file", file);
  if (title) {
    formData.append("title", title);
  }
  return apiFetch("/documents/upload", {
    method: "POST",
    body: formData,
  });
}

/**
 * Deletes a document and its chunks.
 * @param {string} id
 * @returns {Promise<null>}
 */
export async function deleteDocument(id) {
  return apiFetch(`/documents/${id}`, {
    method: "DELETE",
  });
}

